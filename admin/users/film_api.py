"""Вызовы FastAPI для каталога фильмов."""

from django.conf import settings

from clients.films_api.movie_theater_client import AuthenticatedClient as FilmAuthenticatedClient
from clients.films_api.movie_theater_client.api.кинопроизведения.delete_film_api_v1_films_film_id_delete import (
    sync_detailed as delete_film_sync_detailed,
)

from .auth_service import with_token_refresh


def delete_film_via_fastapi(request, film_id: str):
    """DELETE /api/v1/films/{id}; обновление токена — через with_token_refresh (refresh только в auth API)."""
    if not request.session.get("access_token"):
        return None

    @with_token_refresh(
        api_base_url=settings.FASTAPI_URL,
        client_cls=FilmAuthenticatedClient,
    )
    def _delete(req, client):
        return delete_film_sync_detailed(film_id=film_id, client=client)

    return _delete(request)
