"""Клиент Яндекс OAuth"""

from urllib.parse import urlencode

import httpx

from src.core.config import settings

YANDEX_PROVIDER = "yandex"


def build_url_to_authorize_in_yandex(state: str) -> str:
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


async def get_yandex_tokens_by_code(code: str) -> dict:
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


async def get_yandex_profile(access_token: str) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            settings.YANDEX_OAUTH_USERINFO_ENDPOINT,
            headers={"Authorization": f"OAuth {access_token}"},
        )
        response.raise_for_status()

        return response.json()
