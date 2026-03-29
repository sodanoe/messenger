"""
WebSocket endpoint  –  GET /ws?token=<jwt>

Жизненный цикл:
  1. Валидируем JWT из query-param ?token=
  2. manager.connect(user_id, ws)
  3. Redis SET user:online:{id} EX 30
  4. Рассылаем контактам {type: user_online}
  5. Receive-loop: любое сообщение от клиента -> redis.expire (heartbeat)
  6. On disconnect: manager.disconnect / Redis DEL / {type: user_offline}
"""
import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jose import JWTError

from app.core.connection_manager import manager
from app.core.database import AsyncSessionLocal
from app.core.jwt import decode_access_token
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
            c.contact_user_id for c in contacts
            if c.status == ContactStatus.accepted
        ]


@router.websocket("/ws")
async def websocket_endpoint(
    ws: WebSocket,
    token: str = Query(..., description="JWT access token"),
) -> None:
    # ── 1. Auth ────────────────────────────────────────────────────────────
    try:
        user_id = decode_access_token(token)
    except (JWTError, ValueError, Exception):
        await ws.close(code=1008)
        return

    redis = get_redis()
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
        while True:
            await ws.receive_text()
            await redis.expire(f"user:online:{user_id}", 30)

    except WebSocketDisconnect:
        logger.info("WS close user_id=%s (clean disconnect)", user_id)
    except Exception as exc:
        logger.warning("WS error user_id=%s: %s", user_id, exc)

    # ── 4. Cleanup ─────────────────────────────────────────────────────────
    finally:
        manager.disconnect(user_id)
        await redis.delete(f"user:online:{user_id}")
        await manager.send_to_many(
            contact_ids,
            {"type": "user_offline", "user_id": user_id},
        )
        logger.info("WS cleaned user_id=%s", user_id)