import redis.asyncio as aioredis

from app.core.config import settings

_redis: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    """Return a shared Redis client singleton."""
    global _redis
    if _redis is None:
        _redis = aioredis.Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=100,
        )
    return _redis