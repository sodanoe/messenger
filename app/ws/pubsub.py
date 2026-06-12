"""Redis Pub/Sub bridge для multi-worker WebSocket доставки."""

import asyncio
import json
import logging
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

_CHANNEL = "ws:signals"
_RECONNECT_DELAY = 5
_INBOX_TTL = 300
_PING_INTERVAL = 30


async def publish(user_id: int, payload: dict) -> None:
    from app.core.redis_client import get_redis

    redis = get_redis()
    msg_json = json.dumps(payload)
    try:
        pipe = redis.pipeline()
        pipe.rpush(f"ws:inbox:{user_id}", msg_json)
        pipe.expire(f"ws:inbox:{user_id}", _INBOX_TTL)
        pipe.publish(_CHANNEL, str(user_id))
        await pipe.execute()
    except Exception as exc:
        logger.error("Failed to publish for user_id=%s: %s", user_id, exc)


async def drain_inbox(user_id: int) -> None:
    """Дренирует inbox юзера в его WS-очередь. Идемпотентно."""
    from app.core.redis_client import get_redis
    from app.ws.manager import manager

    # Нет активного сокета — нечего дренировать прямо сейчас.
    # Сообщения останутся в inbox (TTL=_INBOX_TTL) и будут забраны
    # явным drain_inbox() из websocket_endpoint при подключении.
    if not await manager.has_connection(user_id):
        return

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

            while True:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=_PING_INTERVAL,
                )

                if message is None:
                    # Тишина в канале _PING_INTERVAL секунд — пингуем
                    # именно это (pubsub) соединение, чтобы Redis/прокси
                    # не закрыли его по idle-таймауту.
                    await pubsub.ping()
                    continue

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

        except (
            aioredis.TimeoutError,
            aioredis.ConnectionError,
            aioredis.BusyLoadingError,
        ) as exc:
            logger.warning(
                "Redis connection lost (%s), reconnecting in %ds...",
                exc.__class__.__name__,
                _RECONNECT_DELAY,
            )

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
