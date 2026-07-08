"""Async Redis client singleton."""
from functools import lru_cache

from redis.asyncio import Redis

from unimatch.config import get_settings


@lru_cache
def get_redis_client() -> Redis:
    settings = get_settings()
    return Redis.from_url(settings.REDIS_URL, decode_responses=True)


async def get_redis() -> Redis:
    """FastAPI dependency returning the Redis client."""
    return get_redis_client()
