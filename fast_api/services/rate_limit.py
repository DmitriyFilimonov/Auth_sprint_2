from fastapi import Depends, Request
from db.redis import get_redis
from core.rate_limiter import check_rate_limit


async def rate_limit(request: Request):
    """
    Зависимость для проверки лимита запросов.
    В эндпоинтах: _ = Depends(rate_limit)
    """
    redis = get_redis()
    return await check_rate_limit(request, redis)