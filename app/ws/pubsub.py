"""Redis Pub/Sub bridge для multi-worker WebSocket доставки."""

import asyncio
import json
import logging

logger = logging.getLogger(__name__)

_CHANNEL = "ws:out"


async def publish(user_id: int, payload: dict) -> None:
    """Publish a websocket event. Called from services instead of manager.send_to."""
    from app.core.redis_client import get_redis

    message = json.dumps({"user_id": user_id, "payload": payload})
    try:
        await get_redis().publish(_CHANNEL, message)
    except Exception as exc:
        logger.error("Failed to publish to Redis: %s", exc)


async def start_listener() -> None:
    """Background task: subscribe to Redis channel and deliver to local manager."""
    from app.core.redis_client import get_redis
    from app.ws.manager import manager

    redis = get_redis()
    pubsub = redis.pubsub()

    try:
        await pubsub.subscribe(_CHANNEL)
        logger.info("WS pubsub listener started channel=%s", _CHANNEL)

        async for message in pubsub.listen():
            if message["type"] != "message":
                continue

            try:
                data = json.loads(message["data"])
                user_id = data["user_id"]
                payload = data["payload"]

                # Отправляем локальному пользователю
                success = await manager.send_to(user_id, payload)
                if not success:
                    logger.debug(
                        "User %s not connected to this worker, message skipped",
                        user_id
                    )

            except json.JSONDecodeError as exc:
                logger.warning("Failed to decode pubsub message: %s", exc)
            except Exception as exc:
                logger.error("pubsub delivery error: %s", exc, exc_info=True)

    except asyncio.CancelledError:
        logger.info("WS pubsub listener cancelled, unsubscribing...")
        try:
            await pubsub.unsubscribe(_CHANNEL)
        except Exception:
            pass
        raise
    except Exception as exc:
        logger.error("WS pubsub listener crashed: %s", exc, exc_info=True)
        raise


async def publish_to_many(user_ids: list[int], payload: dict) -> None:
    """Publish to multiple users via Redis Pub/Sub."""
    if not user_ids:
        return

    # Публикуем параллельно для скорости
    tasks = [publish(uid, payload) for uid in user_ids]
    await asyncio.gather(*tasks, return_exceptions=True)