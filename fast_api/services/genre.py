import json
from functools import lru_cache

from elasticsearch import AsyncElasticsearch, NotFoundError, BadRequestError
from fastapi import Depends
from redis.asyncio import Redis

from db.elastic import get_elastic
from db.redis import get_redis
from models.genre import Genre
from services.base import Service, GetMixin, Cache, Database

GENRE_CACHE_EXPIRE_IN_SECONDS = 60 * 5  # 5 минут


class GenreService(GetMixin, Service):
    """Бизнес-логика по работе с жанрами."""

    def __init__(self, cache: Cache, database: Database):
        self.cache = cache
        self.database = database

    async def get_by_id(self, item_id: str) -> Genre | None:
        """
        Возвращает объект жанра.

        :param item_id: ID жанра
        :return: Модель жанра
        """
        # Пытаемся получить данные из кеша
        genre = await self._genre_from_cache(item_id)
        if not genre:
            # Если жанра нет в кеше, ищем его в базе данных
            genre = await self._get_genre_from_database(item_id)
            if not genre:
                return None
            # Сохраняем жанр в кеш
            await self._put_genre_to_cache(genre)

        return genre

    async def get(
        self,
        page: int,
        size: int,
    ) -> list[Genre] | None:
        """
        Возвращает список жанров по заданным критериям.

        :param page: Номер страницы
        :param size: Количество записей
        :return: Список жанров
        """
        return await self._get_genre_by_filters(page, size)

    async def search(
        self,
        page: int,
        size: int,
    ) -> list[Genre] | None:
        """Возвращает список найденных жанров"""
        query = {
            "from": (page - 1) * size,
            "size": size,
        }

        try:
            doc = await self.database.search(
                index="genres",
                body=query,
            )
        except (BadRequestError, NotFoundError):
            return None

        return [Genre(**hit["_source"]) for hit in doc["hits"]["hits"]]

    async def _get_genre_by_filters(
        self,
        page: int = 1,
        size: int = 50,
    ) -> list[Genre] | None:
        """Поиск жанров по критериям"""

        cache_key = await self._get_genres_cache_key(page, size)
        cached_genres = await self._genres_from_cache(cache_key)
        if cached_genres:
            return cached_genres

        genres = await self._get_genres_from_database(page, size)
        if not genres:
            return None

        await self._put_genres_to_cache(cache_key, genres)

        return genres

    async def _get_genres_from_database(
        self,
        page: int,
        size: int,
    ) -> list[Genre] | None:
        """Получение жанров из базы данных по заданным критериям"""

        query = {
            "query": {
                "bool": {"must": []},
            },
            "sort": [
                {"name": {"order": "asc"}},
            ],
            "from": (page - 1) * size,
            "size": size,
        }

        try:
            doc = await self.database.search(
                index="genres",
                body=query,
            )
        except (BadRequestError, NotFoundError):
            return None

        return [Genre(**hit["_source"]) for hit in doc["hits"]["hits"]]

    async def _get_genre_from_database(self, genre_id: str) -> Genre | None:
        """Получение жанра по ID из базы данных"""
        try:
            doc = await self.database.get(index="genres", id=genre_id)
        except NotFoundError:
            return None
        return Genre(**doc["_source"])

    async def _genre_from_cache(self, genre_id: str) -> Genre | None:
        """Поиск жанра по ID в кэше"""
        data = await self.cache.get(f"genre_{genre_id}")
        if not data:
            return None

        genre = Genre.parse_raw(data)
        return genre

    async def _put_genre_to_cache(self, genre: Genre):
        """Сохранение жанра в кэш"""
        await self.cache.set(
            f"genre_{genre.uuid}", genre.json(), ex=GENRE_CACHE_EXPIRE_IN_SECONDS
        )

    async def _get_genres_cache_key(self, page: int, size: int) -> str:
        """Генерация ключа кэша"""
        return f"genres:page_{page}:size_{size}"

    async def _genres_from_cache(self, cache_key: str) -> list[Genre] | None:
        """Получение жанров из кэша"""
        data = await self.cache.get(cache_key)
        if not data:
            return None
        return [Genre(**item) for item in json.loads(data)]

    async def _put_genres_to_cache(self, cache_key: str, genres: list[Genre]):
        """Сохранение жанров в кэш"""
        await self.cache.set(
            cache_key,
            json.dumps([genre.dict() for genre in genres], sort_keys=True),
            ex=GENRE_CACHE_EXPIRE_IN_SECONDS,
        )


@lru_cache()
def get_genre_service(
    cache: Redis = Depends(get_redis),
    database: AsyncElasticsearch = Depends(get_elastic),
) -> GenreService:
    """Провайдер GenreService"""
    return GenreService(cache, database)
