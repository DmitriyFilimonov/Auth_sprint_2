"""Вызовы Auth API из Django (OpenAPI-клиент)."""

from django.conf import settings

from clients.auth_api.auth_api_client import AuthenticatedClient
from clients.auth_api.auth_api_client.api.пользователи.logout_users_logout_post import (
    sync_detailed as logout_sync_detailed,
)


def _normalize_bearer_token(raw_token: str) -> str:
    """AuthenticatedClient сам добавляет префикс Bearer."""
    token = raw_token.strip()
    if token.startswith("Bearer "):
        return token[7:].strip()
    if token.startswith("Bearer"):
        return token[6:].lstrip()
    return token


def logout_from_auth_service(request) -> None:
    raw_token = request.session.get("access_token")
    if not raw_token:
        return
    token = _normalize_bearer_token(raw_token)
    if not token:
        return
    client = AuthenticatedClient(base_url=settings.AUTH_API_URL, token=token)
    try:
        logout_sync_detailed(client=client)
    except Exception:
        pass
