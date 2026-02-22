from logging import config as logging_config
from pathlib import Path

from pydantic_settings import BaseSettings

from core.logger import LOGGING

# Применяем настройки логирования
logging_config.dictConfig(LOGGING)


class Settings(BaseSettings):
    # Переменные прокидываются в окружение контейнера на этапе сборки
    debug: bool = False
    base_dir: Path = Path(__file__).resolve().parent.parent
    project_name: str = 'Movie theater'
    postgres_user: str
    postgres_password: str
    postgres_host: str
    postgres_port: str
    postgres_db: str
    redis_host: str = ...
    redis_port: int = 6379
    elastic_host: str = ...
    elastic_port: int = 9200
    elastic_schema: str = 'http://'

    auth_service_host: str
    auth_service_port: int
    auth_service_authenticate_token_endpoint: str

    postgres_async_driver: str


settings = Settings()
