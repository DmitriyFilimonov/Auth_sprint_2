import secrets

import httpx
from async_fastapi_jwt_auth import AuthJWT
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.postgres import get_session
from src.db.redis_db import consume_yandex_oauth_state, store_yandex_oauth_state_in_redis
from src.db.repository import UserRepository
from src.schemas.token import TokenResponse
from src.services.auth import AuthService
from src.services.yandex_oauth import (
    YANDEX_PROVIDER,
    build_url_to_authorize_in_yandex,
    get_yandex_tokens_by_code,
    get_yandex_profile,
)

router = APIRouter(prefix="/users", tags=["OAuth Yandex"])


@router.get("/oauth/yandex/start")
async def yandex_oauth_start():
    """Редирект на страницу авторизации Яндекса с одноразовым state в Redis."""
    state = secrets.token_urlsafe(32)

    await store_yandex_oauth_state_in_redis(state)

    url_with_state = build_url_to_authorize_in_yandex(state)

    return RedirectResponse(url=url_with_state, status_code=status.HTTP_302_FOUND)


def map_yandex_profile_to_oauth_identity_fields(
    profile: dict,
) -> tuple[str, str, str | None, str | None, str | None]:
    provider_user_id = str(profile.get("id", "")).strip()

    if not provider_user_id:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Yandex profile missing id",
        )

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

    return provider_user_id, login, email, first_name, last_name


@router.get("/oauth/yandex/callback", response_model=TokenResponse)
async def yandex_oauth_callback(
    request: Request,
    session: AsyncSession = Depends(get_session),
    Authorize: AuthJWT = Depends(),
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
):
    """Обмен code на токены Яндекса, поиск/создание пользователя, выдача JWT нашим сервисом."""
    if error:
        msg = error_description or error

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Yandex OAuth error: {msg}",
        )

    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing code or state",
        )

    if not await consume_yandex_oauth_state(state):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired state",
        )

    try:
        token_data = await get_yandex_tokens_by_code(code)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Yandex token exchange failed",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Yandex token exchange unavailable",
        ) from exc

    access_token = token_data.get("access_token")

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Yandex token response missing access_token",
        )

    try:
        profile = await get_yandex_profile(access_token)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Yandex userinfo failed",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Yandex userinfo unavailable",
        ) from exc

    provider_user_id, login, email, first_name, last_name = map_yandex_profile_to_oauth_identity_fields(profile)

    user_repo = UserRepository(session)

    user = await user_repo.get_user_by_oauth(YANDEX_PROVIDER, provider_user_id)

    if not user:
        try:
            user = await user_repo.create_external_user_with_oauth_identity(
                login=login,
                email=email,
                first_name=first_name,
                last_name=last_name,
                provider=YANDEX_PROVIDER,
                provider_user_id=provider_user_id,
            )
        except IntegrityError as exc:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Login or email already registered",
            ) from exc

    auth_service = AuthService(session, Authorize)

    return await auth_service.issue_tokens_for_external_user(
        request, user, login_info="yandex_oauth"
    )
