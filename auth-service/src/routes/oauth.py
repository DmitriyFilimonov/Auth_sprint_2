import secrets

import httpx
from async_fastapi_jwt_auth import AuthJWT
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.postgres import get_session
from src.db.redis_db import consume_oauth_state, store_oauth_state
from src.db.repository import UserRepository
from src.schemas.token import TokenResponse
from src.services.auth import AuthService
from src.services.oauth_base import OAuthProvider
from src.services.oauth_registry import get_oauth_provider

router = APIRouter(prefix="/users", tags=["OAuth"])


def _resolve_provider(provider_name: str) -> OAuthProvider:
    try:
        return get_oauth_provider(provider_name)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unsupported OAuth provider: {provider_name}",
        )


@router.get("/oauth/{provider_name}/start")
async def oauth_start(provider_name: str):
    """Редирект на страницу авторизации провайдера с одноразовым state в Redis."""
    provider = _resolve_provider(provider_name)

    state = secrets.token_urlsafe(32)

    await store_oauth_state(provider.name, state)

    url_with_state = provider.build_authorization_url(state)

    return RedirectResponse(url=url_with_state, status_code=status.HTTP_302_FOUND)


@router.get("/oauth/{provider_name}/callback", response_model=TokenResponse)
async def oauth_callback(
    provider_name: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
    Authorize: AuthJWT = Depends(),
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
):
    """Обмен code на токены провайдера, поиск/создание пользователя, выдача JWT нашим сервисом."""
    provider = _resolve_provider(provider_name)

    if error:
        msg = error_description or error
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth error from {provider_name}: {msg}",
        )

    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing code or state",
        )

    if not await consume_oauth_state(provider.name, state):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired state",
        )

    try:
        token_data = await provider.exchange_code_for_tokens(code)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Token exchange with {provider_name} failed",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Token exchange with {provider_name} unavailable",
        ) from exc

    access_token = token_data.get("access_token")

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{provider_name} token response missing access_token",
        )

    try:
        profile = await provider.fetch_user_profile(access_token)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Userinfo from {provider_name} failed",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Userinfo from {provider_name} unavailable",
        ) from exc

    try:
        identity = provider.map_profile_to_identity(profile)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Invalid profile from {provider_name}: {exc}",
        ) from exc

    user_repo = UserRepository(session)

    user = await user_repo.get_user_by_oauth(provider.name, identity["provider_user_id"])

    if not user:
        try:
            user = await user_repo.create_external_user_with_oauth_identity(
                login=identity["login"],
                email=identity["email"],
                first_name=identity["first_name"],
                last_name=identity["last_name"],
                provider=provider.name,
                provider_user_id=identity["provider_user_id"],
            )
        except IntegrityError as exc:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Login or email already registered",
            ) from exc

    auth_service = AuthService(session, Authorize)

    return await auth_service.issue_tokens_for_external_user(
        request, user, login_info=f"{provider.name}_oauth"
    )
