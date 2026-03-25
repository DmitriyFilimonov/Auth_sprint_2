import json
from functools import lru_cache

from elasticsearch import AsyncElasticsearch, NotFoundError, BadRequestError
from fastapi import Depends
from redis.asyncio import Redis

from db.elastic import get_elastic
from db.redis import get_redis
from models.person import Person
from models.film import FilmShort
from services.base import Service, SearchMixin, Cache, Database
from services.film_visibility import ELASTIC_EXCLUDE_DELETED_MOVIES

PERSON_CACHE_EXPIRE_IN_SECONDS = 60 * 5  # 5 минут


class PersonService(SearchMixin, Service):
    """Бизнес-логика по работе с фильмами."""

    def __init__(self, cache: Cache, database: Database):
        self.cache = cache
        self.database = database

    async def get_by_id(self, item_id: str) -> Person | None:
        """
        Возвращает объект Person.

        :param item_id: ID персоны
        :return: Модель персоны
        """
        person = await self._person_from_cache(item_id)
        if not person:
            person = await self._get_person_from_database(item_id)
            if not person:
                return None
            await self._put_person_to_cache(person)

        return person

    async def get_film_by_id(self, person_id: str) -> list[FilmShort] | None:
        """
        Возвращает объекты FilmShort.

        :param person_id: ID персоны
        :return: Объекты FilmShort
        """
        films = await self._films_from_cache(person_id)
        if not films:
            films = await self._get_film_by_person_id(person_id)
            if not films:
                return None
            await self._put_films_person_to_cache(person_id, films)

        return films

    async def search(
        self,
        query: str,
        page: int,
        size: int,
    ) -> list[Person] | None:
        """Возвращает список найденных персон"""
        query = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["full_name"],
                    "fuzziness": "AUTO",
                }
            },
            "from": (page - 1) * size,
            "size": size,
        }

        try:
            doc = await self.database.search(
                index="persons",
                body=query,
            )
        except BadRequestError:
            return None
        except NotFoundError:
            return None

        for hit in doc["hits"]["hits"]:
            # Получаем ID персоны
            person_id = hit["_source"]["uuid"]
            # Получаем фильмы и роли персоны
            films = await self._get_film_by_person_id(person_id)
            # Добавляем фильмы к объекту персоны
            hit["_source"]["films"] = films
        return [Person(**hit["_source"]) for hit in doc["hits"]["hits"]]

    async def _get_person_from_database(self, person_id: str) -> Person | None:
        """Получение person по ID из базы данных + его фильмы и роли"""
        try:
            doc = await self.database.get(index="persons", id=person_id)
        except NotFoundError:
            return None

        # Создаем объект персоны
        person = Person(**doc["_source"])
        person.films = await self._get_film_by_person_id(person_id)
        return person

    async def _get_film_by_person_id(self, person_id: str) -> list[FilmShort] | None:
        # Теперь ищем фильмы, где участвует персона
        query = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "bool": {
                                "should": [
                                    {
                                        "nested": {
                                            "path": "actors",
                                            "query": {
                                                "term": {"actors.uuid": person_id}
                                            },
                                        }
                                    },
                                    {
                                        "nested": {
                                            "path": "writers",
                                            "query": {
                                                "term": {"writers.uuid": person_id}
                                            },
                                        }
                                    },
                                    {
                                        "nested": {
                                            "path": "directors",
                                            "query": {
                                                "term": {"directors.uuid": person_id}
                                            },
                                        }
                                    },
                                ],
                                "minimum_should_match": 1,
                            }
                        }
                    ],
                    "must_not": [ELASTIC_EXCLUDE_DELETED_MOVIES],
                }
            }
        }

        try:
            search_result = await self.database.search(
                index="movies",
                body=query,
                size=1000,
            )
        except (NotFoundError, BadRequestError):
            search_result = {"hits": {"hits": []}}

        films = []

        for hit in search_result["hits"]["hits"]:
            film_data = hit["_source"]
            film_roles = []

            # Проверяем в каких ролях персона участвует
            if any(actor["uuid"] == person_id for actor in film_data.get("actors", [])):
                film_roles.append("actor")
            if any(
                writer["uuid"] == person_id for writer in film_data.get("writers", [])
            ):
                film_roles.append("writer")
            if any(
                director["uuid"] == person_id
                for director in film_data.get("directors", [])
            ):
                film_roles.append("director")

            films.append(
                FilmShort(
                    uuid=film_data["uuid"],
                    title=film_data["title"],
                    imdb_rating=film_data.get("imdb_rating"),
                    roles=film_roles,
                )
            )

        return films

    async def _person_from_cache(self, person_id: str) -> Person | None:
        """Поиск person по ID в кэше"""
        data = await self.cache.get(f"person_{person_id}")
        if not data:
            return None

        person = Person.parse_raw(data)
        return person

    async def _films_from_cache(self, person_id: str) -> list[FilmShort] | None:
        """Поиск films по ID в кэше"""
        data = await self.cache.get(f"films_person_{person_id}")
        if not data:
            return None

        films_data = json.loads(data)
        films = [FilmShort(**film) for film in films_data]
        return films

    async def _put_person_to_cache(self, person: Person):
        """Сохранение person в кэш"""
        await self.cache.set(
            f"person_{person.uuid}", person.json(), ex=PERSON_CACHE_EXPIRE_IN_SECONDS
        )

    async def _put_films_person_to_cache(self, person_id: str, films: list[FilmShort]):
        """Сохранение person films в кэш"""
        films_json = json.dumps([film.dict() for film in films], sort_keys=True)

        await self.cache.set(
            f"films_person_{person_id}", films_json, ex=PERSON_CACHE_EXPIRE_IN_SECONDS
        )


@lru_cache()
def get_person_service(
    cache: Redis = Depends(get_redis),
    database: AsyncElasticsearch = Depends(get_elastic),
) -> PersonService:
    """Провайдер PersonService"""
    return PersonService(cache, database)
