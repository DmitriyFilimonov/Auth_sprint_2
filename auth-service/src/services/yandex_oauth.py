from urllib.parse import urlencode

import httpx

from src.core.config import settings
from src.services.oauth_base import OAuthProvider

YANDEX_PROVIDER = "yandex"


class YandexOAuthProvider(OAuthProvider):
    """Клиент Yandex OAuth, реализующий контракт провайдера."""

    @property
    def name(self) -> str:
        return YANDEX_PROVIDER

    def build_authorization_url(self, state: str) -> str:
        params = {
            "response_type": "code",
            "client_id": settings.YANDEX_CLIENT_ID,
            "redirect_uri": settings.YANDEX_REDIRECT_URI,
            "scope": settings.YANDEX_OAUTH_SCOPE,
            "state": state,
        }

        base = settings.YANDEX_OAUTH_AUTH_ENDPOINT.rstrip("?&")

        sep = "?" if "?" not in base else "&"

        return f"{base}{sep}{urlencode(params)}"

    async def exchange_code_for_tokens(self, code: str) -> dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                settings.YANDEX_OAUTH_TOKEN_ENDPOINT,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": settings.YANDEX_CLIENT_ID,
                    "client_secret": settings.YANDEX_CLIENT_SECRET,
                    "redirect_uri": settings.YANDEX_REDIRECT_URI,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()

            return response.json()

    async def fetch_user_profile(self, access_token: str) -> dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                settings.YANDEX_OAUTH_USERINFO_ENDPOINT,
                headers={"Authorization": f"OAuth {access_token}"},
            )
            response.raise_for_status()

            return response.json()

    def map_profile_to_identity(self, profile: dict) -> dict:
        provider_user_id = str(profile.get("id", "")).strip()

        if not provider_user_id:
            raise ValueError("Yandex profile missing id")

        login = (profile.get("login") or "").strip() or f"yandex_{provider_user_id}"
        email = profile.get("default_email")

        if not email and isinstance(profile.get("emails"), list) and profile["emails"]:
            email = profile["emails"][0]

        if email is not None:
            email = str(email).strip() or None

        first_name = profile.get("first_name")
        last_name = profile.get("last_name")

        if first_name is not None:
            first_name = str(first_name).strip() or None

        if last_name is not None:
            last_name = str(last_name).strip() or None

        return {
            "provider_user_id": provider_user_id,
            "login": login,
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
        }


yandex_provider = YandexOAuthProvider()
