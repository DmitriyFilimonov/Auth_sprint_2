from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query


from db.postgres import get_session
from db.films_repository import FilmsRepository
from services.auth import check_admin_role
from services.film import FilmService, get_film_service
from .models import (
    FilmFullResponse,
    FilmShortResponse,
    FilmBaseResponse,
    FilmListResponse,
    Genre,
)
from sqlalchemy.ext.asyncio import AsyncSession


# Объект router, в котором регистрируем обработчики
router = APIRouter()


@router.get(
    "/{film_id}",
    response_model=FilmFullResponse,
    summary="Получить информацию о кинопроизведении",
    description="Возвращает полную информацию о кинопроизведении по его идентификатору",
    response_description="Объект с информацией о кинопроизведении",
)
async def film_details(
    film_id: str = Path(
        ..., example="3d825f60-9fff-4dfe-b294-1a45fa1e115d", description="UUID фильма"
    ),
    film_service: FilmService = Depends(get_film_service),
) -> FilmFullResponse:
    """Получение информацию о кинопроизведении по идентификатору"""
    try:
        UUID(film_id, version=4)
    except ValueError:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Invalid film ID format. Must be a valid UUID v4.",
        )

    film = await film_service.get_by_id(film_id)
    if not film:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="film not found")

    return FilmFullResponse(
        uuid=film.uuid,
        title=film.title,
        imdb_rating=film.imdb_rating,
        description=film.description,
        genres=[genre.model_dump() for genre in film.genres] if film.genres else None,
        actors=[actor.model_dump() for actor in film.actors] if film.actors else None,
        writers=(
            [writer.model_dump() for writer in film.writers] if film.writers else None
        ),
        directors=(
            [director.model_dump() for director in film.directors]
            if film.directors
            else None
        ),
    )


@router.get(
    "/",
    response_model=FilmListResponse,
    summary="Получить список фильмов по заданным критериям",
    description="Возвращает список из короткой информации по кинопроизведениям по заданным фильтрам",
    response_description="Объект с полями items и total",
)
async def list_films(
    sort: str = Query(
        "-imdb_rating",
        regex="^-?imdb_rating$",
        description="Сортировка (-imdb_rating для DESC, imdb_rating для ASC)",
    ),
    genre: UUID | None = Query(
        None,
        description="UUID жанра для фильтрации",
    ),
    page: int = Query(
        1,
        ge=1,
        description="Номер страницы",
    ),
    size: int = Query(
        50,
        ge=1,
        le=100,
        description="Количество элементов на странице (1-100)",
    ),
    film_service: FilmService = Depends(get_film_service),
) -> FilmListResponse:
    """
    Получить список фильмов с возможностью:
    - Сортировки по рейтингу (по убыванию или возрастанию)
    - Фильтрации по жанру
    - Пагинации
    """
    page_data = await film_service.get(
        sort=sort,
        genre=genre,
        page=page,
        size=size,
    )

    items = []

    for item in page_data.items:
        items.append(
            FilmShortResponse(
                uuid=item.uuid,
                title=item.title,
                imdb_rating=item.imdb_rating,
                genres=[Genre(uuid=g.uuid, name=g.name) for g in (item.genres or [])],
            )
        )

    return FilmListResponse(items=items, total=page_data.total)


@router.get(
    "/search/",
    response_model=list[FilmBaseResponse],
    summary="Поиск кинопроизведений",
    description="Полнотекстовый поиск по названиям и описаниям кинопроизведений",
    response_description="Название и рейтинг фильма",
)
async def search_films(
    query: str = Query(..., min_length=2, description="Поисковый запрос"),
    page: int = Query(1, ge=1, description="Номер страницы"),
    size: int = Query(50, ge=1, le=100, description="Количество элементов"),
    film_service: FilmService = Depends(get_film_service),
) -> list[FilmShortResponse]:
    """Поиск кинопроизведений"""
    films = await film_service.search(query=query, page=page, size=size)

    if not films:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="films not found")

    result = []
    for source in films:
        result.append(
            FilmShortResponse(
                uuid=source.uuid,
                title=source.title,
            )
        )

    return films


@router.delete("/{film_id}")
async def delete_film(
    film_id: str,
    user: dict = Depends(check_admin_role),
    session: AsyncSession = Depends(get_session),
):
    film_repo = FilmsRepository(session)

    deleted = await film_repo.delete_single(film_id)

    if not deleted:
        raise HTTPException(404, detail="Not found")

    return user
