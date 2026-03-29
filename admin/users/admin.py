# users/admin.py

import logging
from http import HTTPStatus


from django.conf import settings
from django.contrib import admin, messages

from clients.films_api.movie_theater_client import Client
from clients.films_api.movie_theater_client.api.кинопроизведения.list_films_api_v1_films_get import (
    sync_detailed as list_films_sync_detailed,
)
from clients.films_api.movie_theater_client.models.http_validation_error import (
    HTTPValidationError,
)
from clients.films_api.movie_theater_client.types import Unset
from clients.auth_api.auth_api_client import AuthenticatedClient
from clients.auth_api.auth_api_client.api.пользователи.get_login_history_users_login_history_get import (
    sync_detailed,
)
from users.models import FilmListing, LoginHistory

from .admin_site import admin_site
from .auth_service import with_token_refresh
from .film_api import delete_film_via_fastapi
from .pagination import FilmAPIPaginator
from .querysets import FilmListingQuerySet, LoginHistoryQuerySet

logger = logging.getLogger(__name__)


@with_token_refresh
def _login_history_api(request, client: AuthenticatedClient):
    return sync_detailed(client=client)


def _list_films_page(request, list_per_page: int):
    page = int(request.GET.get("p", 0)) + 1
    client = Client(base_url=settings.FASTAPI_URL)
    return list_films_sync_detailed(
        client=client,
        page=page,
        size=list_per_page,
        sort="-imdb_rating",
    )


class LoginHistoryAdmin(admin.ModelAdmin):
    list_display = ("user_id", "user_agent", "created_at")

    show_full_result_count = False
    list_filter = ()
    search_fields = ()
    ordering = ()

    def get_queryset(self, request):
        try:
            response = _login_history_api(request)
            if response is None:
                return LoginHistoryQuerySet([], model=LoginHistory)
            if response.status_code == 200 and response.parsed is not None:
                return LoginHistoryQuerySet(response.parsed, model=LoginHistory)
        except Exception as e:
            logger.error(
                "Login history: запрос к AUTH_API_URL (%s) не выполнен: %s. ",
                settings.AUTH_API_URL,
                e,
            )

        return LoginHistoryQuerySet([], model=LoginHistory)


class FilmListingAdmin(admin.ModelAdmin):
    list_display = ("title", "imdb_rating", "genres_display")
    list_display_links = None

    list_per_page = 50
    show_full_result_count = True
    list_filter = ()
    search_fields = ()
    ordering = ()

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        return bool(
            getattr(request.user, "is_admin", False) or request.user.is_superuser
        )

    def delete_model(self, request, obj):
        resp = delete_film_via_fastapi(request, obj.uuid)
        if resp is None:
            messages.error(
                request,
                "Нет access token в сессии. Выйдите и войдите в админку снова.",
            )
            return
        if resp.status_code == HTTPStatus.OK:
            messages.success(
                request,
                f"Фильм «{obj.title}» удалён из каталога.",
            )
            return
        if resp.status_code == HTTPStatus.NOT_FOUND:
            messages.error(request, "Фильм не найден в базе каталога.")
            return
        if resp.status_code == HTTPStatus.FORBIDDEN:
            messages.error(
                request,
                "Недостаточно прав (нужна роль admin в токене для FastAPI).",
            )
            return
        messages.error(
            request,
            f"Не удалось удалить фильм (HTTP {resp.status_code}).",
        )

    def delete_queryset(self, request, queryset):
        ok = 0
        failed = 0
        for obj in queryset:
            resp = delete_film_via_fastapi(request, obj.uuid)
            if resp is None:
                failed += 1
            elif resp.status_code == HTTPStatus.OK:
                ok += 1
            else:
                failed += 1
        if ok:
            self.message_user(
                request,
                f"Удалено фильмов: {ok}.",
                level=messages.SUCCESS,
            )
        if failed:
            self.message_user(
                request,
                f"Не удалось удалить записей: {failed} (проверьте сессию и роль admin).",
                level=messages.WARNING,
            )

    def get_queryset(self, request):
        per_page = self.list_per_page
        try:
            response = _list_films_page(request, per_page)
            if response is None:
                return FilmListingQuerySet([], total=0, model=FilmListing)
            if response.status_code != HTTPStatus.OK:
                return FilmListingQuerySet([], total=0, model=FilmListing)
            parsed = response.parsed
            if parsed is None or isinstance(parsed, HTTPValidationError):
                return FilmListingQuerySet([], total=0, model=FilmListing)
            items = parsed.items
            if isinstance(items, Unset):
                items_list = []
            else:
                items_list = items
            return FilmListingQuerySet(
                items_list, total=parsed.total, model=FilmListing
            )
        except Exception as e:
            print(f"films list get_queryset error: {e}", flush=True)

        return FilmListingQuerySet([], total=0, model=FilmListing)

    def get_paginator(
        self,
        request,
        queryset,
        per_page,
        orphans=0,
        allow_empty_first_page=True,
    ):
        total = queryset.count()
        return FilmAPIPaginator(
            list(queryset),
            per_page,
            total,
            orphans=orphans,
            allow_empty_first_page=allow_empty_first_page,
        )


admin_site.register(LoginHistory, LoginHistoryAdmin)
admin_site.register(FilmListing, FilmListingAdmin)
