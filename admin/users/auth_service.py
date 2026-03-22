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


def with_token_refresh(fn):
    def wrapper(request):
        client = AuthenticatedClient(
            base_url=settings.AUTH_API_URL, token=request.session["access_token"]
        )
        response = fn(request, client)

        if response.status_code != HTTPStatus.UNAUTHORIZED:
            return response

        refreshed = refresh_session_tokens(request)

        if refreshed is True:
            client = AuthenticatedClient(
                base_url=settings.AUTH_API_URL, token=request.session["access_token"]
            )

            response = fn(request, client)

            return response

        return response

    return wrapper


@with_token_refresh
def logout_from_auth_service(request, client):
    return logout_sync_detailed(client=client)
