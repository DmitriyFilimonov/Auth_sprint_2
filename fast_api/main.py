from contextlib import asynccontextmanager

from redis.asyncio import Redis
from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from elasticsearch import AsyncElasticsearch

from db import elastic, redis
from core.config import settings
from api.v1 import films, genres, persons
from services.middleware import RateLimitMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Подключаемся к базам при старте сервера
    redis.redis = Redis(host=settings.redis_host, port=settings.redis_port)
    elastic.es = AsyncElasticsearch(
        hosts=[f'{settings.elastic_schema}{settings.elastic_host}:{settings.elastic_port}']
    )
    yield
    # Отключаемся от баз при завершении работы
    await redis.redis.close()
    await elastic.es.close()
app = FastAPI(
    # Конфигурируем название проекта. Оно будет отображаться в документации
    title=settings.project_name,
    description="Информация о фильмах, жанрах и людях, участвовавших в создании произведения",
    version="1.0.0",
    # Адрес документации в красивом интерфейсе
    docs_url='/api/openapi',
    # Адрес документации в ReDoc
    redoc_url="/api/redoc",
    # Адрес документации в формате OpenAPI
    openapi_url='/api/openapi.json',
    # Можно сразу сделать небольшую оптимизацию сервиса
    # и заменить стандартный JSON-сериализатор на более шуструю версию, написанную на Rust
    default_response_class=ORJSONResponse,
    lifespan=lifespan,

)

app.add_middleware(RateLimitMiddleware)

# Подключаем роутер к серверу, указав префикс /v1/films
# Теги указываем для удобства навигации по документации
app.include_router(films.router, prefix='/api/v1/films', tags=['Кинопроизведения'])

app.include_router(genres.router, prefix='/api/v1/genres', tags=['Жанры'])

app.include_router(persons.router, prefix='/api/v1/persons', tags=['Персоны'])
