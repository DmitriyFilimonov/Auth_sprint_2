from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PostgresSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='postgres_')
    dbname: str = Field(..., alias='POSTGRES_DB')
    host: str = ...
    port: int = 5432
    user: str = ...
    password: str = ...

    dbschema: str = 'content'
    tables: list[dict] = [
        {'name': 'film_work', 'batch_size': 100},
        {'name': 'genre', 'batch_size': 1},
        {'name': 'person', 'batch_size': 100},
    ]
    main_table: str = 'film_work'

    def get_dsn(self) -> dict[str, Any]:
        return self.model_dump(
            include={'host', 'port', 'dbname', 'user', 'password'})


class ElasticSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='elastic_')
    host: str = ...
    port: str = 9200

    indices: list[str] = ['movies', 'genres', 'persons']

    def get_host(self) -> str:
        return f'http://{self.host}:{self.port}'


class Settings(BaseSettings):
    # Variables are thrown into the container environment at the build stage
    debug: bool = False
    base_dir: Path = Path(__file__).resolve().parent.parent
    state_path: Path = base_dir / 'storage/state_storage.json'
    main_loop_time: int = 1 * 60
    backoff_time: int = 3 * 60
    postgres_settings: PostgresSettings = PostgresSettings()
    elastic_settings: ElasticSettings = ElasticSettings()


settings = Settings()
