# users/admin.py

from django.contrib import admin

from users.models import LoginHistory

from clients.auth_api.auth_api_client import AuthenticatedClient
from clients.auth_api.auth_api_client.api.пользователи.get_login_history_users_login_history_get import (
    sync_detailed,
)

from .admin_site import admin_site
from .auth_service import with_token_refresh
from .querysets import LoginHistoryQuerySet


@with_token_refresh
def _login_history_api(request, client: AuthenticatedClient):
    return sync_detailed(client=client)


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
            print(f"login history get_query_set error: {e}", flush=True)

        return LoginHistoryQuerySet([], model=LoginHistory)


admin_site.register(LoginHistory, LoginHistoryAdmin)
