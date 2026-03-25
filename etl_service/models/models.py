from dataclasses import dataclass
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class BaseDocument(BaseModel):
    """Base class for Elasticsearch models."""
    uuid: str = Field(alias='id', default=None)

    @field_validator('uuid', mode='before')
    @classmethod
    def transform_uuid(cls, raw_id: UUID | str) -> str:
        return str(raw_id)


class Movie(BaseDocument):
    """Pydantic model for Movies."""
    title: str
    is_deleted: bool = False
    description: str | None = Field(default=None)
    imdb_rating: float | None = Field(alias='rating', default=None)
    genres: list[dict] = Field(default=[])
    directors: list[dict] = Field(default=[])
    directors_names: list[str] = Field(default=[])
    actors: list[dict] = Field(default=[])
    actors_names: list[str] = Field(default=[])
    writers: list[dict] = Field(default=[])
    writers_names: list[str] = Field(default=[])


class Genre(BaseDocument):
    """Pydantic model for Genres."""
    name: str
    description: str | None = Field(default=None)


class Person(BaseDocument):
    """Pydantic model for Persons."""
    full_name: str


@dataclass
class PersonRoles:
    """Dataclass with list of Persons roles."""
    roles = ['director', 'actor', 'writer']
