import json

from functools import lru_cache
from uuid import UUID

from elasticsearch import AsyncElasticsearch, NotFoundError, BadRequestError
from fastapi import Depends
from redis.asyncio import Redis

from db.elastic import get_elastic
from db.redis import get_redis
from .models import FilmListResult
from models.film import Film
from services.base import Service, GetMixin, SearchMixin, Cache, Database

FILM_CACHE_EXPIRE_IN_SECONDS = 60 * 5  # 5 минут


class FilmService(SearchMixin, GetMixin, Service):
    """Бизнес-логика по работе с фильмами."""

    def __init__(self, cache: Cache, database: Database):
        self.cache = cache
        self.database = database

    async def get_by_id(self, item_id: str) -> Film | None:
        """
        Возвращает объект фильма. Он опционален, так как фильм может отсутствовать в базе.

        :param item_id: ID кинопроизведения
        :return: Модель кинопроизведения
        """
        # Пытаемся получить данные из кеша, потому что оно работает быстрее
        film = await self._film_from_cache(item_id)
        if not film:
            # Если фильма нет в кеше, то ищем его в базе данных
            film = await self._get_film_from_database(item_id)
            if not film:
                # Если он отсутствует в базе данных, значит, фильма вообще нет
                return None
            # Сохраняем фильм в кеш
            await self._put_film_to_cache(film)

        return film

    async def get(
        self, sort: str, genre: UUID | None, page: int, size: int
    ) -> FilmListResult:
        return await self._get_films_by_filters(sort, genre, page, size)

    async def search(self, query: str, page: int, size: int) -> list[Film] | None:
        """Возвращает список найденных фильмов"""
        query = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["title^3", "description"],
                    "fuzziness": "AUTO",
                }
            },
            "from": (page - 1) * size,
            "size": size,
        }

        try:
            doc = await self.database.search(index="movies", body=query)
        except BadRequestError:
            return None
        except NotFoundError:
            return None

        return [Film(**hit["_source"]) for hit in doc["hits"]["hits"]]

    async def _get_films_by_filters(
        self,
        sort: str = "-imdb_rating",
        genre: UUID | None = None,
        page: int = 1,
        size: int = 50,
    ) -> FilmListResult:
        """Поиск фильмов по критериям"""
        cache_key = await self._get_films_cache_key(sort, genre, page, size)
        cached_films = await self.cache.get(cache_key)
        if cached_films is not None:
            try:
                return self._film_list_from_cache_blob(cached_films)
            except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                pass

        films = await self._get_films_from_database(sort, genre, page, size)

        if films.total != 0:
            await self._put_films_to_cache(
                cache_key=cache_key,
                films=films.items,
                total=films.total,
            )

        return films

    async def _get_films_from_database(
        self,
        sort: str,
        genre: UUID | None,
        page: int,
        size: int,
    ) -> FilmListResult:
        """Получение фильмов из базы данных по заданным критериям"""
        sort_order = "desc" if sort.startswith("-") else "asc"
        sort_field = sort.lstrip("-")

        bool_query: dict = {"bool": {"must": []}}
        if genre:
            bool_query["bool"]["must"].append(
                {
                    "nested": {
                        "path": "genres",
                        "query": {"term": {"genres.uuid": str(genre)}},
                    }
                }
            )

        try:
            count_doc = await self.database.count(
                index="movies",
                body={"query": bool_query},
            )
        except BadRequestError:
            return FilmListResult(items=[], total=0)
        except NotFoundError:
            return FilmListResult(items=[], total=0)

        total_val = int(count_doc["count"])

        if total_val == 0:
            return FilmListResult(items=[], total=0)

        start = (page - 1) * size

        if start >= total_val:
            return FilmListResult(items=[], total=total_val)

        search_body = {
            "query": bool_query,
            "sort": [{sort_field: {"order": sort_order}}],
            "from": start,
            "size": size,
        }

        try:
            doc = await self.database.search(
                index="movies",
                body=search_body,
            )
        except BadRequestError:
            return FilmListResult(items=[], total=total_val)
        except NotFoundError:
            return FilmListResult(items=[], total=total_val)

        films = [Film(**hit["_source"]) for hit in doc["hits"]["hits"]]
        return FilmListResult(items=films, total=total_val)

    async def _get_film_from_database(self, film_id: str) -> Film | None:
        """Получение фильма по ID из базы данных"""
        try:
            doc = await self.database.get(index="movies", id=film_id)
        except NotFoundError:
            return None
        return Film(**doc["_source"])

    async def _film_from_cache(self, film_id: str) -> Film | None:
        """Поиск фильма по ID в кэше"""
        data = await self.cache.get(f"film_{film_id}")
        if not data:
            return None

        film = Film.parse_raw(data)
        return film

    async def _put_film_to_cache(self, film: Film):
        """Сохранение фильма в кэш"""
        await self.cache.set(
            f"film_{film.uuid}", film.json(), FILM_CACHE_EXPIRE_IN_SECONDS
        )

    async def _get_films_cache_key(
        self, sort: str, genre: UUID | None, page: int, size: int
    ) -> str:
        """Генерация ключа кэша"""
        genre_part = f":genre_{genre}" if genre else ""
        return f"films:sort_{sort}{genre_part}:page_{page}:size_{size}"

    def _film_list_from_cache_blob(self, raw: str) -> FilmListResult:
        """Разбор JSON из Redis в FilmListResult."""
        payload = json.loads(raw)
        total = int(payload["total"])
        items = [Film.model_validate(item) for item in payload["items"]]
        return FilmListResult(items=items, total=total)

    async def _put_films_to_cache(self, cache_key: str, films: list[Film], total: int):
        """Сохранение фильмов в кэш"""
        blob = json.dumps(
            {"total": total, "items": [film.model_dump(mode="json") for film in films]}
        )
        await self.cache.set(cache_key, blob, FILM_CACHE_EXPIRE_IN_SECONDS)


@lru_cache()
def get_film_service(
    cache: Redis = Depends(get_redis),
    database: AsyncElasticsearch = Depends(get_elastic),
) -> FilmService:
    """Провайдер FilmService"""
    return FilmService(cache, database)
