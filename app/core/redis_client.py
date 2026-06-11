import redis.asyncio as aioredis
from redis.asyncio.retry import Retry
from redis.backoff import ExponentialBackoff
from redis.exceptions import TimeoutError, ConnectionError

from app.core.config import settings

_redis: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    """Return a shared Redis client singleton with proper timeouts."""
    global _redis
    if _redis is None:
        _redis = aioredis.Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=100,
            socket_timeout=30,  # <- таймаут на операцию
            socket_connect_timeout=10,  # <- таймаут на подключение
            socket_keepalive=True,  # <- держать соединение живым
            retry_on_timeout=True,  # <- повторять при таймауте
            retry=Retry(
                ExponentialBackoff(cap=10, base=1),
                retries=3,
                supported_errors=(TimeoutError, ConnectionError),
            ),
        )
    return _redis


async def close_redis() -> None:
    """Gracefully close Redis connection pool."""
    global _redis
    if _redis is not None:
        await _redis.close()
        _redis = None
