"""
WebSocket endpoint  –  GET /ws?ticket=<one-time-ticket>

Жизненный цикл:
  1. Валидируем одноразовый тикет из Redis
  2. manager.connect(user_id, ws)
  3. Redis SET user:online:{id} EX 30
  4. Рассылаем контактам {type: user_online}
  5. Receive-loop: heartbeat + обновление contact_ids каждые 10 пингов
  6. On disconnect: manager.disconnect / Redis DEL / {type: user_offline}
"""

import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.connection_manager import manager
from app.core.database import AsyncSessionLocal
from app.core.redis_client import get_redis
from app.models.contact import ContactStatus
from app.repositories.contact_repo import ContactRepository

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


async def _get_accepted_contact_ids(user_id: int) -> list[int]:
    """Return all accepted contact user_ids for the given user."""
    async with AsyncSessionLocal() as db:
        repo = ContactRepository(db)
        contacts = await repo.list_for_user(user_id)
        return [
            c.contact_user_id for c in contacts if c.status == ContactStatus.accepted
        ]


@router.websocket("/ws")
async def websocket_endpoint(
    ws: WebSocket,
    ticket: str = Query(..., description="One-time WS ticket from /auth/ws/ticket"),
) -> None:
    # ── 1. Auth ────────────────────────────────────────────────────────────
    redis = get_redis()
    user_id_str = await redis.getdel(f"ws:ticket:{ticket}")
    if not user_id_str:
        await ws.close(code=1008)
        return
    user_id = int(user_id_str)

    contact_ids = await _get_accepted_contact_ids(user_id)

    # ── 2. Connect + presence ──────────────────────────────────────────────
    await manager.connect(user_id, ws)
    await redis.set(f"user:online:{user_id}", "1", ex=30)

    await manager.send_to_many(
        contact_ids,
        {"type": "user_online", "user_id": user_id},
    )
    logger.info("WS open  user_id=%s  contacts=%s", user_id, contact_ids)

    # ── 3. Receive loop (heartbeat) ────────────────────────────────────────
    try:
        heartbeat_count = 0
        while True:
            await ws.receive_text()
            await redis.expire(f"user:online:{user_id}", 30)
            heartbeat_count += 1
            # Обновляем список контактов каждые 10 пингов (~3 минуты)
            if heartbeat_count % 10 == 0:
                contact_ids = await _get_accepted_contact_ids(user_id)
                logger.debug("WS refreshed contacts user_id=%s", user_id)

    except WebSocketDisconnect:
        logger.info("WS close user_id=%s (clean disconnect)", user_id)
    except Exception as exc:
        logger.warning("WS error user_id=%s: %s", user_id, exc)

    # ── 4. Cleanup ─────────────────────────────────────────────────────────
    finally:
        manager.disconnect(user_id)
        await redis.delete(f"user:online:{user_id}")
        # Свежий список — мог измениться за время сессии
        fresh_contact_ids = await _get_accepted_contact_ids(user_id)
        await manager.send_to_many(
            fresh_contact_ids,
            {"type": "user_offline", "user_id": user_id},
        )
        logger.info("WS cleaned user_id=%s", user_id)
