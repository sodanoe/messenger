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
            max_connections=10,
            socket_timeout=5,
            socket_connect_timeout=3,
            socket_keepalive=True,
            retry_on_timeout=False,
        )
    return _redis


async def close_redis() -> None:
    """Gracefully close Redis connection pool."""
    global _redis
    if _redis is not None:
        await _redis.close()
        _redis = None