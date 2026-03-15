from fastapi import Request, HTTPException, status, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.db.redis_db import get_redis
from src.core.rate_limiter import check_rate_limit


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/users/"):
            redis_client = await get_redis()
            is_allowed = await check_rate_limit(request, redis_client)

            if not is_allowed:
               return Response(status_code=status.HTTP_429_TOO_MANY_REQUESTS)

            await check_rate_limit(request, redis_client)

        response = await call_next(request)
        return response