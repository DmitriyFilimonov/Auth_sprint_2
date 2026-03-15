from fastapi import Request, HTTPException, status, Response
from starlette.middleware.base import BaseHTTPMiddleware
from db import redis as redis_db
from core.rate_limiter import check_rate_limit


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/api/"):
            redis_client = redis_db.redis
            is_allowed = await check_rate_limit(request, redis_client)

            if not is_allowed:
               return Response(status_code=status.HTTP_429_TOO_MANY_REQUESTS)

            await check_rate_limit(request, redis_client)

        response = await call_next(request)
        return response