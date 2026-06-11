"""Redis Pub/Sub bridge для multi-worker WebSocket доставки."""

import asyncio
import json
import logging

logger = logging.getLogger(__name__)

_CHANNEL = "ws:out"
_RECONNECT_DELAY = 5  # секунд между попытками переподключения
_CHANNEL = "ws:signals"
_INBOX_TTL = 300  # 5 минут


async def publish(user_id: int, payload: dict) -> None:
    from app.core.redis_client import get_redis

    redis = get_redis()
    msg_json = json.dumps(payload)
    try:
        pipe = redis.pipeline()
        # 1. Кладём в inbox — персистентно, с TTL
        pipe.rpush(f"ws:inbox:{user_id}", msg_json)
        pipe.expire(f"ws:inbox:{user_id}", _INBOX_TTL)
        # 2. Сигнал listener'у: "у этого юзера есть pending"
        pipe.publish(_CHANNEL, str(user_id))
        await pipe.execute()
    except Exception as exc:
        logger.error("Failed to publish for user_id=%s: %s", user_id, exc)


async def drain_inbox(user_id: int) -> None:
    """Дренирует inbox юзера в его WS-очередь. Идемпотентно."""
    from app.core.redis_client import get_redis
    from app.ws.manager import manager

    redis = get_redis()
    while True:
        msg_json = await redis.lpop(f"ws:inbox:{user_id}")
        if not msg_json:
            break
        try:
            payload = json.loads(msg_json)
            await manager.send_to(user_id, payload)
        except Exception as exc:
            logger.error("drain_inbox error user_id=%s: %s", user_id, exc)


async def start_listener() -> None:
    from app.core.redis_client import get_redis

    while True:
        pubsub = None
        try:
            redis = get_redis()
            pubsub = redis.pubsub()
            await pubsub.subscribe(_CHANNEL)
            logger.info("WS pubsub listener started channel=%s", _CHANNEL)

            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                try:
                    user_id = int(message["data"])
                    await drain_inbox(user_id)
                except Exception as exc:
                    logger.error("pubsub delivery error: %s", exc, exc_info=True)

        except asyncio.CancelledError:
            if pubsub:
                try:
                    await pubsub.unsubscribe(_CHANNEL)
                    await pubsub.aclose()
                except Exception:
                    pass
            raise
        except Exception as exc:
            logger.error("WS pubsub listener crashed: %s", exc, exc_info=True)
        finally:
            if pubsub:
                try:
                    await pubsub.unsubscribe(_CHANNEL)
                    await pubsub.aclose()
                except Exception:
                    pass

        await asyncio.sleep(_RECONNECT_DELAY)


async def publish_to_many(user_ids: list[int], payload: dict) -> None:
    if not user_ids:
        return
    await asyncio.gather(
        *(publish(uid, payload) for uid in user_ids),
        return_exceptions=True,
    )
