import asyncio

import aiohttp
import backoff
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from core.config import settings

security = HTTPBearer()

AUTH_SERVICE_UNAVAILABLE_DETAIL = (
    "Сервис авторизации временно недоступен. "
    "Доступ к защищённым данным сейчас невозможен — попробуйте позже."
)


class AuthServiceError(Exception):
    """Временная ошибка Auth API (502/503/504) — повторяем с backoff."""


@backoff.on_exception(
    backoff.expo,
    (aiohttp.ClientError, asyncio.TimeoutError, AuthServiceError),
    max_tries=settings.auth_service_max_retries,
    jitter=backoff.full_jitter,
    base=2,
    factor=0.5,
)
async def _call_auth_service(url: str, credentials: str) -> dict:
    timeout = aiohttp.ClientTimeout(total=settings.auth_service_request_timeout_seconds)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(
            url,
            headers={"Authorization": f"Bearer {credentials}"},
        ) as resp:
            if resp.status == 200:
                return await resp.json()
            if resp.status == 401:
                raise HTTPException(
                    status_code=401,
                    detail="Unauthorized",
                )
            if resp.status in (502, 503, 504):
                raise AuthServiceError(f"upstream status {resp.status}")
            raise HTTPException(
                status_code=401,
                detail="Unauthorized",
            )


async def authenticate_token(auth: HTTPAuthorizationCredentials = Security(security)):
    """
    Проверка access-токена через Auth API с повторными попытками при сетевых сбоях
    и ответом 503 с понятным текстом после исчерпания backoff.
    """
    url = (
        f"http://{settings.auth_service_host}:{settings.auth_service_port}"
        f"{settings.auth_service_authenticate_token_endpoint}"
    )
    try:
        return await _call_auth_service(url, auth.credentials)
    except HTTPException:
        raise
    except (aiohttp.ClientError, asyncio.TimeoutError, AuthServiceError) as exc:
        raise HTTPException(
            status_code=503,
            detail=AUTH_SERVICE_UNAVAILABLE_DETAIL,
        ) from exc


ADMIN_ROLES = frozenset({"admin", "superuser"})


async def check_admin_role(user: dict = Depends(authenticate_token)):
    if not user:
        return None

    if user.get("role") not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Только для админов")

    return user
