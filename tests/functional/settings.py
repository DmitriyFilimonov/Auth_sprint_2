from dataclasses import dataclass

from pydantic_settings import BaseSettings, SettingsConfigDict


class ElasticSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='elastic_')
    host: str = ...
    port: str = "9200"

    indices: list[str] = ['movies', 'genres', 'persons']

    def get_host(self) -> str:
        return f'http://{self.host}:{self.port}'


class RedisSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='redis_')
    host: str = ...
    port: str = "6379"


class FastAPISettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='fastapi_')
    host: str = ...
    port: str = "8000"

    def get_host(self) -> str:
        return f'http://{self.host}:{self.port}'


class AuthAPISettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='auth_')
    host: str = ...
    port: str = "8000"

    def get_host(self) -> str:
        return f'http://{self.host}:{self.port}'


class AuthDBSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='auth_db_')
    host: str
    port: str = "5432"

    superuser_password: str

    def get_host(self) -> str:
        return f'{self.host}:{self.port}'


@dataclass
class ElasticSchemas:
    """Dataclass with index schemas for ElasticLoader."""
    base_settings = {
        "settings": {
            "refresh_interval": "1s",
            "analysis": {
                "filter": {
                    "english_stop": {"type": "stop", "stopwords": "_english_"},
                    "english_stemmer": {"type": "stemmer",
                                        "language": "english"},
                    "english_possessive_stemmer": {
                        "type": "stemmer",
                        "language": "possessive_english"
                    },
                    "russian_stop": {"type": "stop", "stopwords": "_russian_"},
                    "russian_stemmer": {"type": "stemmer",
                                        "language": "russian"}
                },
                "analyzer": {
                    "ru_en": {
                        "tokenizer": "standard",
                        "filter": [
                            "lowercase",
                            "english_stop",
                            "english_stemmer",
                            "english_possessive_stemmer",
                            "russian_stop",
                            "russian_stemmer"
                        ]
                    }
                }
            }
        }
    }

    movies = {
        "mappings": {
            "dynamic": "strict",
            "properties": {
                "uuid": {"type": "keyword"},
                "title": {
                    "type": "text",
                    "analyzer": "ru_en",
                    "fields": {
                        "raw": {"type": "keyword"}
                    }
                },
                "description": {"type": "text", "analyzer": "ru_en"},
                "imdb_rating": {"type": "float"},
                "genres": {
                    "type": "nested",
                    "dynamic": "strict",
                    "properties": {
                        "uuid": {"type": "keyword"},
                        "name": {"type": "keyword"}
                    }
                },
                "directors": {
                    "type": "nested",
                    "dynamic": "strict",
                    "properties": {
                        "uuid": {"type": "keyword"},
                        "full_name": {"type": "text", "analyzer": "ru_en"}
                    }
                },
                "directors_names": {"type": "text", "analyzer": "ru_en"},
                "actors": {
                    "type": "nested",
                    "dynamic": "strict",
                    "properties": {
                        "uuid": {"type": "keyword"},
                        "full_name": {"type": "text", "analyzer": "ru_en"}
                    }
                },
                "actors_names": {"type": "text", "analyzer": "ru_en"},
                "writers": {
                    "type": "nested",
                    "dynamic": "strict",
                    "properties": {
                        "uuid": {"type": "keyword"},
                        "full_name": {"type": "text", "analyzer": "ru_en"}
                    }
                },
                "writers_names": {"type": "text", "analyzer": "ru_en"}
            }
        }
    }

    genres = {
        "mappings": {
            "dynamic": "strict",
            "properties": {
                "uuid": {"type": "keyword"},
                "name": {"type": "keyword"},
                "description": {"type": "text", "analyzer": "ru_en"}
            }
        }
    }

    persons = {
        "mappings": {
            "dynamic": "strict",
            "properties": {
                "uuid": {"type": "keyword"},
                "full_name": {
                    "type": "text",
                    "analyzer": "ru_en",
                    "fields": {
                        "raw": {"type": "keyword"}
                    }
                }
            }
        }
    }

    def get_schema(self, index_name: str) -> dict:
        """Get schema by index name."""
        mappings = getattr(self, index_name)
        return {**self.base_settings, **mappings}


class TestSettings(BaseSettings):
    debug: bool = False
    elastic_settings: ElasticSettings = ElasticSettings()
    redis_settings: RedisSettings = RedisSettings()
    fastapi_settings: FastAPISettings = FastAPISettings()

    auth_settings: AuthAPISettings = AuthAPISettings()
    auth_db_setting: AuthDBSettings = AuthDBSettings()

    elastic_mappings: ElasticSchemas = ElasticSchemas()

    def es_index_mapping(self, es_index) -> dict:
        return self.elastic_mappings.get_schema(es_index)


test_settings = TestSettings()
