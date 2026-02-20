from async_fastapi_jwt_auth import AuthJWT
from pydantic import BaseModel

from src.core.config import settings
from src.db.redis_db import is_access_token_revoked, is_refresh_token_valid


class AuthJWTSettings(BaseModel):
    authjwt_secret_key: str = settings.SECRET_KEY
    authjwt_algorithm: str = settings.ALGORITHM
    authjwt_access_token_expires: int = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    authjwt_refresh_token_expires: int = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    authjwt_token_location: set = {"headers"}
    authjwt_cookie_csrf_protect: bool = False
    authjwt_denylist_enabled: bool = True
    authjwt_denylist_token_checks: set = {"access", "refresh"}


@AuthJWT.load_config
def get_config():
    return AuthJWTSettings()


@AuthJWT.token_in_denylist_loader
async def token_checker(decoded_token):
    jti = decoded_token["jti"]
    token_type = decoded_token["type"]

    if token_type == "access":
        return await is_access_token_revoked(jti)

    if token_type == "refresh":
        return not await is_refresh_token_valid(jti)

    return True
