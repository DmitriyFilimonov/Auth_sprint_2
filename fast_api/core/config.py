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
    redis_host: str = ...
    redis_port: int = 6379
    elastic_host: str = ...
    elastic_port: int = 9200
    elastic_schema: str = 'http://'


settings = Settings()
