from dataclasses import dataclass
import logging

import elasticsearch
from elasticsearch import Elasticsearch, helpers

from core.backoff import backoff


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
                "is_deleted": {"type": "boolean"},
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


class ElasticLoader:
    """Loader to Elasticsearch."""
    def __init__(self, indices: list[str]):
        self.indices = indices
        self.indices_schemas = ElasticSchemas()
        self.logger = logging.getLogger(__name__)

    @backoff(elasticsearch.ConnectionError)
    def load_data(self, client: Elasticsearch, extracted_data: dict) -> None:
        """Load data into Elasticsearch using bulk."""
        index = extracted_data.get('index')
        self.logger.info(f'Load data into Elasticsearch /{index}')
        actions = [
            {
                '_index': index,
                '_id': row['uuid'],
                '_source': row
            }
            for row in extracted_data.get('data')
        ]
        helpers.bulk(client, actions)

    @backoff(elasticsearch.ConnectionError)
    def check_indices_exists(self, client: Elasticsearch) -> None:
        """Check Elasticsearch indices exists and create if not."""
        for index in self.indices:
            try:
                if not client.indices.exists(index=index):
                    index_body = self.indices_schemas.get_schema(index)
                    client.indices.create(index=index, body=index_body)
                    self.logger.warning(f'Created index /{index}')
            except Exception:
                self.logger.error(f'Failed to create index {index}')
                raise
