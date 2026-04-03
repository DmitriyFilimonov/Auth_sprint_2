import datetime
import os

from starlette.requests import Request


async def check_rate_limit(
    request: Request,
    redis,
    *,
    limit: int | None = None,
    env_var: str = "REQUEST_LIMIT_PER_SECOND",
    default_limit: int = 20,
    scope: str = "app",
) -> bool:
    """
    Проверяет лимит запросов для клиента (по IP).
    Возвращает True, если запрос можно обработать, иначе False (лимит превышен).

    scope — префикс ключа в Redis, например, у каждого сервиса свой префикс.
    """
    if limit is None:
        raw = os.getenv(env_var)
        limit = int(raw) if raw is not None else default_limit

    ip = request.headers.get("x-real-ip") or (
        request.client.host if request.client else ""
    )

    pipe = redis.pipeline()
    now = datetime.datetime.now()
    key = f"{scope}:{ip}:{now.strftime('%Y%m%d%H%M%S')}"
    pipe.incr(key, 1)
    pipe.expire(key, 1)
    result = await pipe.execute()

    request_number = result[0]
    return request_number <= limit
