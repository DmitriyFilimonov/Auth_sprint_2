from http import HTTPStatus

from django.conf import settings

from clients.auth_api.auth_api_client import AuthenticatedClient
from clients.auth_api.auth_api_client.api.пользователи.logout_users_logout_post import (
    sync_detailed as logout_sync_detailed,
)
from clients.auth_api.auth_api_client.api.пользователи.refresh_token_users_refresh_post import (
    sync_detailed as refresh_sync_detailed,
)


def refresh_session_tokens(request) -> bool:
    refresh_token = request.session.get("refresh_token")

    client = AuthenticatedClient(base_url=settings.AUTH_API_URL, token=refresh_token)

    response = refresh_sync_detailed(client=client)

    if response.status_code != HTTPStatus.OK:
        return False

    if response.parsed is None:
        return False

    request.session["access_token"] = response.parsed.access_token
    request.session["refresh_token"] = response.parsed.refresh_token

    return True


def with_token_refresh(fn=None, *, api_base_url=None, client_cls=None):
    """
    Вызывает fn(request, client) с Bearer из сессии; при 401 обновляет токены через auth API и повторяет.

    api_base_url: куда слать запросы (по умолчанию AUTH_API_URL).
    client_cls: класс клиента из того же OpenAPI-пакета, что и вызываемый метод
    (по умолчанию AuthenticatedClient из auth_api; для FastAPI — из movie_theater_client).
    Обновление сессии по-прежнему только через refresh_session_tokens (auth API).
    """

    ClientCls = client_cls or AuthenticatedClient

    def decorator(f):
        def wrapper(request):
            base = api_base_url if api_base_url is not None else settings.AUTH_API_URL
            client = ClientCls(base_url=base, token=request.session["access_token"])
            response = f(request, client)

            if response.status_code != HTTPStatus.UNAUTHORIZED:
                return response

            refreshed = refresh_session_tokens(request)

            if refreshed is True:
                client = ClientCls(base_url=base, token=request.session["access_token"])

                response = f(request, client)

                return response

            return response

        return wrapper

    if fn is not None:
        return decorator(fn)
    return decorator


@with_token_refresh
def logout_from_auth_service(request, client):
    return logout_sync_detailed(client=client)
