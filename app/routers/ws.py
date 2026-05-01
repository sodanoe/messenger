"""
WebSocket endpoint  –  GET /ws?ticket=<one-time-ticket>

Жизненный цикл:
  1. Валидируем одноразовый тикет из Redis
  2. manager.connect(user_id, ws)
  3. Redis SET user:online:{id} EX 30
  4. Рассылаем контактам {type: user_online}
  5. Отправляем себе статусы контактов которые уже онлайн
  6. Receive-loop: heartbeat + обновление contact_ids каждые 10 пингов
  7. On disconnect: manager.disconnect / Redis DEL / {type: user_offline}
"""

import asyncio
import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.ws.manager import manager
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


async def _safe_send_json(ws: WebSocket, data: dict) -> bool:
    """
    Безопасная отправка JSON с обработкой всех возможных ошибок WebSocket.
    Возвращает True если отправка успешна.
    """
    try:
        from starlette.websockets import WebSocketState

        if ws.client_state != WebSocketState.CONNECTED:
            logger.debug(
                "Skip send: socket state=%s data_type=%s",
                ws.client_state,
                data.get("type"),
            )
            return False

        await ws.send_json(data)
        return True
    except WebSocketDisconnect:
        logger.debug("Cannot send: client disconnected (type=%s)", data.get("type"))
        return False
    except RuntimeError as exc:
        logger.debug("Cannot send: %s (type=%s)", exc, data.get("type"))
        return False
    except Exception as exc:
        logger.warning("Unexpected error sending %s: %s", data.get("type"), exc)
        return False


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

    # Один pipeline вместо N последовательных запросов к Redis
    online_contacts = []
    if contact_ids:
        pipe = redis.pipeline()
        for cid in contact_ids:
            pipe.exists(f"user:online:{cid}")
        presences = await pipe.execute()
        online_contacts = [cid for cid, alive in zip(contact_ids, presences) if alive]

    if online_contacts:
        success = await _safe_send_json(
            ws, {"type": "contacts_online", "user_ids": online_contacts}
        )
        if not success:
            logger.warning(
                "Failed to send initial online contacts to user_id=%s, "
                "connection might be unstable",
                user_id,
            )

    logger.info("WS open  user_id=%s  contacts=%s", user_id, contact_ids)

    # ── 3. Receive loop (heartbeat) ────────────────────────────────────────
    try:
        heartbeat_count = 0
        while True:
            try:
                message = await asyncio.wait_for(ws.receive(), timeout=35.0)

                # Если клиент закрыл соединение
                if message["type"] == "websocket.disconnect":
                    logger.info("WS client disconnected user_id=%s", user_id)
                    break

                # Нас интересует только факт получения (heartbeat)
                if message["type"] == "websocket.receive":
                    await redis.expire(f"user:online:{user_id}", 30)
                    heartbeat_count += 1

                    # Обновляем список контактов каждые 10 пингов (~3 минуты)
                    if heartbeat_count % 10 == 0:
                        new_contact_ids = await _get_accepted_contact_ids(user_id)
                        if set(new_contact_ids) != set(contact_ids):
                            logger.info(
                                "WS contacts changed user_id=%s old=%s new=%s",
                                user_id,
                                len(contact_ids),
                                len(new_contact_ids),
                            )
                            contact_ids = new_contact_ids

            except asyncio.TimeoutError:
                logger.info("WS heartbeat timeout user_id=%s", user_id)
                break
            except WebSocketDisconnect:
                logger.info("WS client disconnected user_id=%s", user_id)
                break

    except WebSocketDisconnect:
        logger.info("WS close user_id=%s (clean disconnect)", user_id)
    except Exception as exc:
        logger.warning("WS error user_id=%s: %s", user_id, exc)

    # ── 4. Cleanup ─────────────────────────────────────────────────────────
    finally:
        await manager.disconnect(user_id, ws)
        await redis.delete(f"user:online:{user_id}")

        # Используем contact_ids из памяти (обновляется каждые 10 heartbeat).
        # Лишний DB-запрос при disconnect не нужен — уведомляем тех кого знаем.
        if contact_ids:
            await manager.send_to_many(
                contact_ids,
                {"type": "user_offline", "user_id": user_id},
            )

        logger.info("WS cleaned user_id=%s", user_id)
