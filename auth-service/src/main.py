from contextlib import asynccontextmanager

from async_fastapi_jwt_auth.exceptions import (
    AuthJWTException,
    JWTDecodeError,
    RevokedTokenError,
    MissingTokenError,
    RefreshTokenRequired,
    AccessTokenRequired,
)
from fastapi import FastAPI, Request
from fastapi.openapi.utils import get_openapi
from fastapi.responses import ORJSONResponse
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis
from starlette.responses import JSONResponse
from jwt.exceptions import ExpiredSignatureError

from src.core.config import settings
from src.db import redis_db as redis
from src.db import postgres
from src.services.middleware import RateLimitMiddleware
import src.auth.jwt  # НЕ УДАЛЯТЬ # noqa\
from src.routes import users, oauth_yandex


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Подключаемся к базам при старте сервера
    redis.redis = Redis(host=settings.redis_host, port=settings.redis_port)

    yield

    # Отключаемся от баз при завершении работы
    await redis.redis.close()
    await postgres.engine.dispose()


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Auth API",
        version="1.0.0",
        description="JWT authentication",
        routes=app.routes,
    )

    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
    }

    openapi_schema["security"] = [{"BearerAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app = FastAPI(
    title=settings.project_name,
    docs_url="/users/openapi",
    redoc_url="/users/redoc",
    openapi_url="/users/openapi.json",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RateLimitMiddleware)

app.openapi = custom_openapi

app.include_router(users.router, tags=["Пользователи"])
app.include_router(oauth_yandex.router)


@app.exception_handler(RevokedTokenError)
async def revoked_token_exception_handler(
    request: Request,
    exc: RevokedTokenError,
):
    return JSONResponse(
        status_code=401,
        content={"detail": exc.message},
    )


@app.exception_handler(MissingTokenError)
async def missing_token_exception_handler(
    request: Request,
    exc: MissingTokenError,
):
    return JSONResponse(
        status_code=401,
        content={"detail": exc.message},
    )


@app.exception_handler(RefreshTokenRequired)
async def refresh_token_required_exception_handler(
    request: Request,
    exc: RefreshTokenRequired,
):
    return JSONResponse(
        status_code=401,
        content={"detail": exc.message},
    )


@app.exception_handler(AccessTokenRequired)
async def access_token_required_exception_handler(
    request: Request,
    exc: AccessTokenRequired,
):
    return JSONResponse(
        status_code=401,
        content={"detail": exc.message},
    )


@app.exception_handler(ExpiredSignatureError)
async def expired_signature_handler(request: Request, exc: ExpiredSignatureError):
    """Явное истечение claim `exp` (PyJWT), не путать с прочими ошибками декодирования."""
    del request, exc
    return JSONResponse(
        status_code=401,
        content={"detail": "Access token has expired"},
    )


@app.exception_handler(JWTDecodeError)
async def jwt_decode_error_handler(request: Request, exc: JWTDecodeError):
    """Прочие ошибки разбора JWT (не только exp)."""

    detail = exc.message

    return JSONResponse(
        status_code=401,
        content={"detail": detail},
    )


# детализация ошибки, не предусмотренной выше
@app.exception_handler(AuthJWTException)
def authjwt_exception_handler(request: Request, exc: AuthJWTException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})
