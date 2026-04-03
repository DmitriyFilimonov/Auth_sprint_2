from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from redis_rate_limit import check_rate_limit

from src.db.redis_db import get_redis


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/users/"):
            redis_client = await get_redis()
            is_allowed = await check_rate_limit(
                request,
                redis_client,
                default_limit=15,
                scope="auth",
            )

            if not is_allowed:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "Too Many Requests"},
                )

        response = await call_next(request)
        return response