import time
from typing import Optional
from redis.asyncio import Redis

redis: Optional[Redis] = None


async def get_redis() -> Redis:
    return redis


async def revoke_access_token(jti: str, exp: int):
    ttl = exp - int(time.time())
    if ttl > 0:
        await redis.setex(f"access:{jti}", ttl, "revoked")


async def is_access_token_revoked(jti: str) -> bool:
    return await redis.exists(f"access:{jti}") == 1


async def store_refresh_token(jti: str, user_id: str, exp: int):
    ttl = exp - int(time.time())
    if ttl > 0:
        await redis.setex(f"refresh:{jti}", ttl, user_id)


async def is_refresh_token_valid(jti: str) -> bool:
    return await redis.exists(f"refresh:{jti}") == 1


async def revoke_refresh_token(jti: str):
    await redis.delete(f"refresh:{jti}")


async def revoke_all_refresh_tokens(user_id: str):
    """
    Logout from all devices
    """
    async for key in redis.scan_iter("refresh:*"):
        uuid = await redis.get(key)
        if uuid == user_id:
            await redis.delete(key)
