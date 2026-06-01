import asyncio
import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.database import AsyncSessionLocal
from app.core.redis_client import get_redis
from app.models.contact import ContactStatus
from app.repositories.contact_repo import ContactRepository
from app.ws.manager import manager
from app.ws.notifier import ChatNotifier

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

    notifier = ChatNotifier()
    await notifier.user_online(contact_ids, user_id)

    # Один pipeline вместо N последовательных запросов к Redis
    online_contacts = []
    if contact_ids:
        pipe = redis.pipeline()
        for cid in contact_ids:
            await pipe.exists(f"user:online:{cid}")
        presences = await pipe.execute()
        online_contacts = [cid for cid, alive in zip(contact_ids, presences) if alive]

    if online_contacts:
        # ИСПРАВЛЕНО: Отправляем строго через менеджер, чтобы избежать гонки за сокет!
        # Метод send_to не блокирует поток и безопасен.
        await manager.send_to(
            user_id, {"type": "contacts_online", "user_ids": online_contacts}
        )

    logger.info("WS open  user_id=%s  contacts=%s", user_id, contact_ids)

    # ── 3. Receive loop (heartbeat) ────────────────────────────────────────
    try:
        heartbeat_count = 0
        while True:
            try:
                # Читаем входящие данные (пинг от клиента)
                message = await asyncio.wait_for(ws.receive(), timeout=35.0)

                if message["type"] == "websocket.disconnect":
                    logger.info("WS client disconnected user_id=%s", user_id)
                    break

                if message["type"] == "websocket.receive":
                    await redis.expire(f"user:online:{user_id}", 30)
                    heartbeat_count += 1

                    # Обновляем список контактов каждые 10 пингов (~3 минуты)
                    if heartbeat_count % 10 == 0:
                        new_contact_ids = await _get_accepted_contact_ids(user_id)

                        if set(new_contact_ids) != set(contact_ids):
                            # ИСПРАВЛЕНО: Логика дифференциации контактов
                            old_set = set(contact_ids)
                            new_set = set(new_contact_ids)

                            # Кого добавили за эти 3 минуты? Уведомляем их, что мы ONLINE
                            added_contacts = list(new_set - old_set)
                            if added_contacts:
                                await notifier.user_online(added_contacts, user_id)

                            # Кого удалили? Уведомляем их, что мы для них OFFLINE
                            removed_contacts = list(old_set - new_set)
                            if removed_contacts:
                                await notifier.user_offline(removed_contacts, user_id)

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

    except Exception as exc:
        logger.warning("WS error user_id=%s: %s", user_id, exc)

    # ── 4. Cleanup ─────────────────────────────────────────────────────────
    finally:
        # Менеджер сам закроет сокет внутри себя корректно
        await manager.disconnect(user_id, ws)
        await redis.delete(f"user:online:{user_id}")

        if contact_ids:
            await notifier.user_offline(contact_ids, user_id)

        logger.info("WS cleaned user_id=%s", user_id)
