"""
WebSocket Connection Manager.

Хранит:  user_id → set[WebSocket]  (поддержка нескольких вкладок/устройств)

Singleton `manager` импортируется в роутере /ws и в pubsub listener.
Прямые send_to из сервисов заменены на pubsub.publish — это позволяет
корректно работать при uvicorn --workers N.
"""
import asyncio
import logging
from typing import Dict

from fastapi import WebSocket
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: Dict[int, set[WebSocket]] = {}

    # ── connect / disconnect ──────────────────────────────────────────

    async def connect(self, user_id: int, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.setdefault(user_id, set()).add(ws)
        logger.debug(
            "WS connected: user_id=%s  sockets=%s  total_users=%s",
            user_id,
            len(self._connections[user_id]),
            len(self._connections),
        )

    def disconnect(self, user_id: int, ws: WebSocket) -> None:
        sockets = self._connections.get(user_id)
        if sockets is None:
            return
        sockets.discard(ws)
        if not sockets:
            del self._connections[user_id]
        logger.debug(
            "WS disconnected: user_id=%s  total_users=%s",
            user_id,
            len(self._connections),
        )

    # ── send helpers ──────────────────────────────────────────────────

    async def send_to(self, user_id: int, payload: dict) -> None:
        """Send JSON to all sockets of a user. Silently skips if offline."""
        sockets = self._connections.get(user_id)
        if not sockets:
            return

        dead: set[WebSocket] = set()
        for ws in list(sockets):
            if ws.client_state != WebSocketState.CONNECTED:
                dead.add(ws)
                continue
            try:
                await ws.send_json(payload)
            except Exception as exc:
                logger.warning("send_to user_id=%s failed: %s", user_id, exc)
                dead.add(ws)

        for ws in dead:
            self.disconnect(user_id, ws)

    async def send_to_many(self, user_ids: list[int], payload: dict) -> None:
        if not user_ids:
            return
        await asyncio.gather(
            *(self.send_to(uid, payload) for uid in user_ids),
            return_exceptions=True,
        )

    # ── helpers ───────────────────────────────────────────────────────

    def is_connected(self, user_id: int) -> bool:
        return bool(self._connections.get(user_id))

    @property
    def online_user_ids(self) -> list[int]:
        return list(self._connections.keys())


manager = ConnectionManager()
