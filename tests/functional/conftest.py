import asyncio
import uuid

import aiohttp
from elasticsearch import AsyncElasticsearch
import pytest_asyncio
from elasticsearch.helpers import async_bulk

from tests.functional.utils.security import get_password_hash

from .settings import test_settings


from sqlalchemy import text
from tests.functional.db.users import users_engine


@pytest_asyncio.fixture(scope="session")
def event_loop():
    """Фикстура для переопределения event_loop для использования scope session"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest_asyncio.fixture(name="es_client", scope="session")
async def es_client():
    """Фикстура для единоразового создания клиента Elasticsearch"""
    es_client = AsyncElasticsearch(
        hosts=test_settings.elastic_settings.get_host(), verify_certs=False
    )
    yield es_client
    await es_client.close()


@pytest_asyncio.fixture()
async def aiohttp_session():
    """Фикстура для создания одного экземпляра aiohttp.ClientSession  в рамках функции-теста."""
    session = aiohttp.ClientSession()
    yield session
    await session.close()


@pytest_asyncio.fixture(name="es_data_movies", scope="session")
async def es_data_movies():
    """Фикстура для подготовки тестовых данных для Elasticsearch по фильмам"""
    es_data = [
        {
            "uuid": str(uuid.uuid4()),
            "imdb_rating": 8.5,
            "title": "The Star",
            "description": "New World",
            "genres": [
                {"uuid": str(uuid.uuid4()), "name": "Action"},
                {"uuid": str(uuid.uuid4()), "name": "Sci-Fi"},
            ],
            "directors": [{"uuid": str(uuid.uuid4()), "full_name": "Stan"}],
            "actors": [
                {"uuid": str(uuid.uuid4()), "full_name": "Ann"},
                {"uuid": str(uuid.uuid4()), "full_name": "Bob"},
            ],
            "writers": [
                {"uuid": str(uuid.uuid4()), "full_name": "Ben"},
                {"uuid": str(uuid.uuid4()), "full_name": "Howard"},
            ],
            "directors_names": ["Stan"],
            "actors_names": ["Ann", "Bob"],
            "writers_names": ["Ben", "Howard"],
        }
        for _ in range(60)
    ] + [
        {
            "uuid": "608c4567-0b8a-49a0-88fb-82770c5b2f61",
            "imdb_rating": 8.7,
            "title": "The movie",
            "description": "New Super Movie",
            "genres": [
                {"uuid": str(uuid.uuid4()), "name": "Action"},
                {"uuid": str(uuid.uuid4()), "name": "Sci-Fi"},
                {"uuid": "2fec4f4f-7f84-475c-ad28-791ce135bd2e", "name": "TestGenre"},
            ],
            "directors": [{"uuid": str(uuid.uuid4()), "full_name": "Stan"}],
            "actors": [
                {"uuid": str(uuid.uuid4()), "full_name": "Ann"},
                {"uuid": str(uuid.uuid4()), "full_name": "Bob"},
                {"uuid": "88c78458-54c8-455f-846e-82734dc1967f", "full_name": "Maxim"},
            ],
            "writers": [
                {"uuid": str(uuid.uuid4()), "full_name": "Ben"},
                {"uuid": str(uuid.uuid4()), "full_name": "Howard"},
            ],
            "directors_names": ["Stan"],
            "actors_names": ["Ann", "Bob", "Maxim"],
            "writers_names": ["Ben", "Howard"],
        }
    ]

    bulk_query: list[dict] = []
    for row in es_data:
        data = {"_index": "movies", "_id": row["uuid"]}
        data.update({"_source": row})
        bulk_query.append(data)

    return bulk_query


@pytest_asyncio.fixture(name="es_data_genres", scope="session")
async def es_data_genres():
    """Фикстура для подготовки тестовых данных для Elasticsearch по жанрам"""

    es_data = [
        {"uuid": str(uuid.uuid4()), "name": "Action"},
        {"uuid": str(uuid.uuid4()), "name": "Sci-Fi"},
        {"uuid": "2fec4f4f-7f84-475c-ad28-791ce135bd2e", "name": "TestGenre"},
    ]

    bulk_query: list[dict] = []
    for row in es_data:
        data = {"_index": "genres", "_id": row["uuid"]}
        data.update({"_source": row})
        bulk_query.append(data)

    return bulk_query


@pytest_asyncio.fixture(name="es_data_persons", scope="session")
async def es_data_persons():
    """Фикстура для подготовки тестовых данных для Elasticsearch по персонам"""

    es_data = [
        {"uuid": str(uuid.uuid4()), "full_name": f"{person} {str(uuid.uuid4())}"}
        for person in ["Ann", "Bob", "Ben", "Howard", "Stan"] * 10
    ]

    es_data.append(
        {"uuid": "3a6ed55e-6aef-4cd2-932c-808495182425", "full_name": "James"}
    )

    bulk_query: list[dict] = []
    for row in es_data:
        data = {"_index": "persons", "_id": row["uuid"]}
        data.update({"_source": row})
        bulk_query.append(data)

    return bulk_query


@pytest_asyncio.fixture(name="es_write_data")
async def es_write_data(es_client):
    """Фикстура для записи тестовых данных в Elasticsearch"""

    async def inner(data, es_index):
        if await es_client.indices.exists(index=es_index):
            await es_client.indices.delete(index=es_index)
        await es_client.indices.create(
            index=es_index, **test_settings.es_index_mapping(es_index)
        )

        updated, errors = await async_bulk(client=es_client, actions=data)
        await es_client.indices.refresh()

        if errors:
            raise Exception("Ошибка записи данных в Elasticsearch")

    return inner


@pytest_asyncio.fixture(name="make_get_request")
async def make_get_request(aiohttp_session):
    """Фикстура для выполнения GET-запросов к API"""

    async def inner(field: str, endpoint: str, query_data=None):
        if query_data is None:
            query_data = {}
        url = (
            test_settings.fastapi_settings.get_host()
            + "/api/v1"
            + field
            + endpoint
            + "/"
        )
        async with aiohttp_session.get(url, params=query_data) as response:
            body = await response.json()
            status = response.status
        return {"body": body, "status": status}

    return inner


@pytest_asyncio.fixture(name="make_auth_request")
async def make_auth_request(aiohttp_session):
    """Фикстура для выполнения запросов к сервису авторизации"""

    async def inner(method: str, endpoint: str, request_body=None, headers=None):
        if request_body is None:
            request_body = {}
        url = test_settings.auth_settings.get_host() + "/users" + endpoint + "/"
        http_method = getattr(aiohttp_session, method)
        async with http_method(url, json=request_body, headers=headers) as response:
            body = await response.json()
            status = response.status
        return {"body": body, "status": status}

    return inner


@pytest_asyncio.fixture(name="clear_auth_db_tables")
async def clear_auth_db_tables():
    async def inner():
        async with users_engine.begin() as conn:
            tables = "users, roles, history"
            if tables:
                await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE;"))

    return inner


@pytest_asyncio.fixture(name="create_super_user")
async def create_super_user():
    async def inner():
        async with users_engine.begin() as conn:
            user_id = uuid.uuid4()
            login = "admin_test"
            print(test_settings.auth_db_setting.superuser_password)
            hashed_password = get_password_hash(
                test_settings.auth_db_setting.superuser_password
            )

            await conn.execute(
                text(
                    """
                    INSERT INTO users (id, login, password, created_at) 
                    VALUES (:id, :login, :password, NOW())
                """
                ),
                {"id": user_id, "login": login, "password": hashed_password},
            )

            role_id = uuid.uuid4()

            await conn.execute(
                text(
                    "INSERT INTO roles (id, user_id, role, created_at) "
                    "VALUES (:id, :user_id, :role, NOW())"
                ),
                {"id": role_id, "user_id": user_id, "role": "SUPERUSER"},
            )

            return {"login": login}

    return inner
