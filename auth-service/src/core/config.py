from logging import config as logging_config
from pathlib import Path

from pydantic_settings import BaseSettings

from src.core.logger import LOGGING

# Применяем настройки логирования
logging_config.dictConfig(LOGGING)


class Settings(BaseSettings):
    # Переменные прокидываются в окружение контейнера на этапе сборки
    debug: bool = False
    base_dir: Path = Path(__file__).resolve().parent.parent
    project_name: str = 'auth'

    redis_host: str = '127.0.0.1'
    redis_port: int = 6379

    postgres_user: str = 'postgres'
    postgres_password: str = ""
    postgres_host: str
    # при локальной генерации миграций хост из сети docker недоступен
    postgres_migrations_host: str
    postgres_port: int = 5432
    postgres_db: str = 'auth'
    superuser_password: str

    YANDEX_CLIENT_ID: str
    YANDEX_CLIENT_SECRET: str
    YANDEX_REDIRECT_URI: str

    sync_driver: str = 'postgresql+psycopg'
    async_driver: str = 'postgresql+asyncpg'

    # JWT
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:8000"]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8"
    }


settings = Settings()
