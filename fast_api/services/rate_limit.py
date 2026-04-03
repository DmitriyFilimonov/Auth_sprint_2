from fastapi import Depends, Request
from db.redis import get_redis
from redis_rate_limit import check_rate_limit


async def rate_limit(request: Request):
    """
    Зависимость для проверки лимита запросов.
    В эндпоинтах: _ = Depends(rate_limit)
    """
    redis = await get_redis()
    return await check_rate_limit(
        request,
        redis,
        default_limit=20,
        scope="fastapi",
    )