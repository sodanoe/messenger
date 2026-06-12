"""Жизненный цикл одного WS-соединения: connect → heartbeat-loop → cleanup."""

import asyncio
import logging

from fastapi import WebSocket, WebSocketDisconnect

from app.core.database import AsyncSessionLocal
from app.models.contact import ContactStatus
from app.repositories.contact_repo import ContactRepository
from app.ws.manager import manager
from app.ws.notifier import ChatNotifier
from app.ws.pubsub import drain_inbox

logger = logging.getLogger(__name__)

HEARTBEAT_TIMEOUT = 35.0
PRESENCE_TTL = 30
CONTACTS_REFRESH_EVERY = 10  # ~3 минуты при таймауте 35с


async def get_accepted_contact_ids(user_id: int) -> list[int]:
    """Все accepted-контакты юзера. Открывает свою сессию — вызывается из
    долгоживущего WS-соединения, вне обычного per-request db: Depends.
    """
    async with AsyncSessionLocal() as db:
        repo = ContactRepository(db)
        contacts = await repo.list_for_user(user_id)
        return [
            c.contact_user_id for c in contacts if c.status == ContactStatus.accepted
        ]


class WsSession:
    """Один WS-сеанс. Аутентификация (тикет) уже пройдена снаружи —
    сюда приходит готовый user_id.
    """

    def __init__(self, user_id: int, ws: WebSocket, redis) -> None:
        self.user_id = user_id
        self.ws = ws
        self.redis = redis
        self.notifier = ChatNotifier()
        self.contact_ids: list[int] = []
        self.heartbeat_count = 0

    # ── lifecycle ────────────────────────────────────────────────────

    async def connect(self) -> None:
        """Регистрация сокета, presence, дренаж inbox, online-уведомления."""
        self.contact_ids = await get_accepted_contact_ids(self.user_id)

        await manager.connect(self.user_id, self.ws)
        await self.redis.set(f"user:online:{self.user_id}", "1", ex=PRESENCE_TTL)

        await drain_inbox(self.user_id)
        await self.notifier.user_online(self.contact_ids, self.user_id)
        await self._send_online_contacts()

        logger.info("WS open  user_id=%s  contacts=%s", self.user_id, self.contact_ids)

    async def run(self) -> None:
        """Receive-loop: ждём пинги от клиента, обновляем presence,
        периодически диффим список контактов.
        """
        while True:
            try:
                message = await asyncio.wait_for(
                    self.ws.receive(), timeout=HEARTBEAT_TIMEOUT
                )
            except asyncio.TimeoutError:
                logger.info("WS heartbeat timeout user_id=%s", self.user_id)
                return
            except WebSocketDisconnect:
                logger.info("WS client disconnected user_id=%s", self.user_id)
                return

            if message["type"] == "websocket.disconnect":
                logger.info("WS client disconnected user_id=%s", self.user_id)
                return

            if message["type"] == "websocket.receive":
                await self._on_heartbeat()

    async def cleanup(self) -> None:
        """Снять сокет из менеджера; если это было последнее устройство
        юзера — погасить presence и уведомить контакты об offline.
        """
        await manager.disconnect(self.user_id, self.ws)

        if not await manager.has_connection(self.user_id):
            await self.redis.delete(f"user:online:{self.user_id}")
            if self.contact_ids:
                await self.notifier.user_offline(self.contact_ids, self.user_id)

        logger.info("WS cleaned user_id=%s", self.user_id)

    # ── internals ────────────────────────────────────────────────────

    async def _send_online_contacts(self) -> None:
        """Один pipeline вместо N последовательных EXISTS к Redis."""
        if not self.contact_ids:
            return

        pipe = self.redis.pipeline()
        for cid in self.contact_ids:
            pipe.exists(f"user:online:{cid}")
        presences = await pipe.execute()

        online = [cid for cid, alive in zip(self.contact_ids, presences) if alive]
        if online:
            # Через менеджер — не блокирует, безопасно сразу после connect()
            await manager.send_to(
                self.user_id, {"type": "contacts_online", "user_ids": online}
            )

    async def _on_heartbeat(self) -> None:
        await self.redis.expire(f"user:online:{self.user_id}", PRESENCE_TTL)
        self.heartbeat_count += 1

        if self.heartbeat_count % CONTACTS_REFRESH_EVERY == 0:
            await self._refresh_contacts()

    async def _refresh_contacts(self) -> None:
        new_contact_ids = await get_accepted_contact_ids(self.user_id)
        new_set, old_set = set(new_contact_ids), set(self.contact_ids)
        if new_set == old_set:
            return

        # Кого добавили — уведомляем их, что мы ONLINE
        added = list(new_set - old_set)
        if added:
            await self.notifier.user_online(added, self.user_id)

        # Кого удалили — уведомляем их, что мы для них OFFLINE
        removed = list(old_set - new_set)
        if removed:
            await self.notifier.user_offline(removed, self.user_id)

        logger.info(
            "WS contacts changed user_id=%s old=%s new=%s",
            self.user_id,
            len(self.contact_ids),
            len(new_contact_ids),
        )
        self.contact_ids = new_contact_ids
