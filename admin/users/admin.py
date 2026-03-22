# users/admin.py

from django.contrib import admin
from django.conf import settings

from users.models import LoginHistory

from clients.auth_api.auth_api_client import AuthenticatedClient
from clients.auth_api.auth_api_client.api.пользователи.get_login_history_users_login_history_get import (
    sync_detailed,
)

from .admin_site import admin_site
from .auth_service import _normalize_bearer_token
from .querysets import LoginHistoryQuerySet


class LoginHistoryAdmin(admin.ModelAdmin):
    list_display = ("user_id", "user_agent", "created_at")

    # Отключаем всё, что лезет в БД для подсчета и фильтрации
    show_full_result_count = False
    list_filter = ()
    search_fields = ()
    ordering = ()

    def get_queryset(self, request):
        raw = request.session.get("access_token")
        if not raw:
            return LoginHistoryQuerySet([], model=LoginHistory)

        client = AuthenticatedClient(
            base_url=settings.AUTH_API_URL,
            token=_normalize_bearer_token(raw),
        )

        try:
            response = sync_detailed(
                client=client,
                limit=10,
                offset=0,
            )

            if response.status_code == 200 and response.parsed is not None:
                return LoginHistoryQuerySet(response.parsed, model=LoginHistory)

        except Exception as e:
            print(f"login history get_query_set error: {e}", flush=True)

        return LoginHistoryQuerySet([], model=LoginHistory)


admin_site.register(LoginHistory, LoginHistoryAdmin)
