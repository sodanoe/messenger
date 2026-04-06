import redis.asyncio as aioredis

from app.core.config import settings

_pool: aioredis.ConnectionPool | None = None


def get_redis() -> aioredis.Redis:
    """Return a Redis client backed by a shared connection pool."""
    global _pool
    if _pool is None:
        _pool = aioredis.ConnectionPool.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=20,
        )
    return aioredis.Redis(connection_pool=_pool)
