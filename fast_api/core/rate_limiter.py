import os

import datetime
from fastapi import Request


REQUEST_LIMIT_PER_SECOND = int(os.getenv("REQUEST_LIMIT_PER_SECOND", 20))

async def check_rate_limit(request: Request, redis) -> bool:
    """
    Проверяет лимит запросов для клиента (по IP).
    Возвращает True, если запрос можно обработать.
    Выбрасывает HTTPException 429, если лимит превышен.
    """
    ip = request.headers.get("x-real-ip") or request.client.host

    pipe = redis.pipeline()
    now = datetime.datetime.now()
    key = f'rate:{ip}:{now.minute}'
    pipe.incr(key, 1)
    pipe.expire(key, 59)
    result = await pipe.execute()

    request_number = result[0]
    if request_number > REQUEST_LIMIT_PER_SECOND:
        return False

    return True