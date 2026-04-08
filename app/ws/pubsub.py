"""
Redis Pub/Sub bridge для multi-worker WebSocket доставки.

Архитектура:
    сервис
      └─ publish(user_id, payload)      # публикует в Redis
           └─ Redis channel "ws:out"
                └─ start_listener()     # каждый worker слушает
                     └─ manager.send_to(user_id, payload)

Таким образом сообщение доходит до нужного worker'а независимо от того,
к какому worker'у подключён клиент.
"""

import asyncio
import json
import logging

logger = logging.getLogger(__name__)

_CHANNEL = "ws:out"


async def publish(user_id: int, payload: dict) -> None:
    """Publish a websocket event. Called from services instead of manager.send_to."""
    from app.core.redis_client import get_redis

    message = json.dumps({"user_id": user_id, "payload": payload})
    await get_redis().publish(_CHANNEL, message)


async def start_listener() -> None:
    """
    Background task: subscribe to Redis channel and deliver to local manager.
    Runs once per worker process. Launched from lifespan.
    """
    from app.core.redis_client import get_redis
    from app.ws.manager import manager

    # Pub/Sub нужна отдельная клиентская сессия (не из пула)
    redis = get_redis()
    pubsub = redis.pubsub()
    await pubsub.subscribe(_CHANNEL)
    logger.info("WS pubsub listener started  channel=%s", _CHANNEL)

    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            try:
                data = json.loads(message["data"])
                await manager.send_to(data["user_id"], data["payload"])
            except Exception as exc:
                logger.warning("pubsub delivery error: %s", exc)
    except asyncio.CancelledError:
        await pubsub.unsubscribe(_CHANNEL)
        logger.info("WS pubsub listener stopped")
        raise


async def publish_to_many(user_ids: list[int], payload: dict) -> None:
    """Publish a websocket event to multiple users via Redis Pub/Sub."""
    for user_id in user_ids:
        await publish(user_id, payload)
