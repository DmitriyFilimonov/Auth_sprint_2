from datetime import datetime

from pydantic import Field, BaseModel, HttpUrl


class Person(BaseModel):
    """Модель персоны (актёра, режиссёра, сценариста)"""

    uuid: str = Field(
        ...,
        example="5b4bf1bc-3397-4e83-9b17-8b10c6544ed1",
        description="Уникальный идентификатор персоны",
    )
    full_name: str = Field(
        ...,
        example="George Lucas",
        description="Полное имя персоны",
        max_length=255,
    )


class Genre(BaseModel):
    """Модель жанра фильма"""

    uuid: str = Field(
        ...,
        example="3d8d9bf5-0d90-4353-88ba-4ccc5d2c07ff",
        description="Уникальный идентификатор жанра",
    )
    name: str = Field(
        ...,
        example="Action",
        description="Название жанра",
        max_length=50,
    )
    description: str | None = Field(
        None,
        example="Фильмы с динамично развивающимся сюжетом",
        description="Описание жанра",
        max_length=1000,
    )


class FilmBaseResponse(BaseModel):
    """Базовая информация по кинопроизведениям"""

    uuid: str = Field(
        ...,
        example="3d825f60-9fff-4dfe-b294-1a45fa1e115d",
        description="Уникальный идентификатор фильма",
    )
    title: str = Field(
        ...,
        example="Star Wars: Episode IV - A New Hope",
        description="Название кинопроизведения",
        max_length=255,
    )


class FilmShortResponse(FilmBaseResponse):
    """Короткая информация по кинопроизведениям"""

    imdb_rating: float | None = Field(
        None, example=8.6, description="Рейтинг кинопроизведения на IMDB", ge=0, le=10
    )
    genres: list[Genre] | None = Field(
        None, description="Список жанров кинопроизведения"
    )


class FilmListResponse(BaseModel):
    """Список фильмов страницы и общее число записей по фильтру."""

    items: list[FilmShortResponse] = Field([])
    total: int = Field(..., ge=0)


class FilmFullResponse(FilmShortResponse):
    """Полная информация по кинопроизведениям"""

    description: str | None = Field(
        None,
        example="The Imperial Forces...",
        description="Описание кинопроизведения",
        max_length=2000,
    )
    pg_rating: str | None = Field(
        None,
        description="Возрастной рейтинг (PG, PG-13, R и т.д.)",
        example="PG-13",
        max_length=10,
    )
    duration: int | None = Field(
        None,
        description="Длительность фильма в минутах",
        example=120,
        gt=0,
    )
    release_year: int | None = Field(
        None,
        description="Год выпуска кинопроизведения",
        example=1977,
        ge=1888,  # Первый фильм был снят в 1888 году
        le=datetime.now().year + 5,  # Плюс небольшой запас на будущее
    )
    poster_url: HttpUrl | None = Field(
        None,
        description="URL постера фильма",
        example="https://example.com/posters/star_wars.jpg",
    )
    actors: list[Person] | None = Field(
        None,
        description="Список актёров",
    )
    writers: list[Person] | None = Field(
        None,
        description="Список сценаристов",
    )
    directors: list[Person] | None = Field(
        None,
        description="Список режиссёров",
    )


class PersonFilmsRoles(FilmBaseResponse):
    """Модель ролей в фильме"""

    roles: list | None = Field(
        None,
        description="Должность человека",
    )


class PersonFilms(FilmBaseResponse):
    """Модель фильмов с рейтингом"""

    imdb_rating: float | None = Field(
        None,
        example=8.6,
        description="Рейтинг кинопроизведения на IMDB",
        ge=0,
        le=10,
    )


class PersonFullResponse(Person):
    """Полная информация по персоне"""

    films: list | None = Field(
        None,
        description="Список кинопроизведений с должностями человека",
    )


class GenreFullResponse(Genre):
    """Полная информация по жанрам"""

    films: list[FilmBaseResponse] | None = Field(
        None,
        description="Список кинопроизведений",
    )
