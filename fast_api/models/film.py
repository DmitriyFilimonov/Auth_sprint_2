from pydantic import Field
from .base import BaseDocument
from .genre import Genre
from .person import Person


class Film(BaseDocument):
    """Модель фильмов"""
    title: str
    is_deleted: bool = False
    imdb_rating: float | None = None
    description: str | None = None
    genres: list[Genre] | None = None
    actors: list[Person] | None = None
    writers: list[Person] | None = None
    directors: list[Person] | None = None


class FilmShort(BaseDocument):
    title: str
    imdb_rating: float | None = None
    roles: list[str] = None


class FilmDB(BaseDocument):
    title: str
    description: str | None = Field(default=None)
    imdb_rating: float | None = Field(alias='rating', default=None)
    genres: list[dict] = Field(default=[])
    directors: list[dict] = Field(default=[])
    directors_names: list[str] = Field(default=[])
    actors: list[dict] = Field(default=[])
    actors_names: list[str] = Field(default=[])
    writers: list[dict] = Field(default=[])
    writers_names: list[str] = Field(default=[])
