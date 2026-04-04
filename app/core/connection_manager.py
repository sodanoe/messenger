"""
WebSocket Connection Manager.

Singleton `manager` хранит активные соединения user_id → WebSocket.
Используется в роутере /ws и в сервисах (DM, group messages).
"""

import asyncio
import logging
from typing import Dict

from fastapi import WebSocket
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        # user_id → WebSocket
        self._connections: Dict[int, WebSocket] = {}

    # ------------------------------------------------------------------ #
    #  connect / disconnect                                                #
    # ------------------------------------------------------------------ #

    async def connect(self, user_id: int, ws: WebSocket) -> None:
        """Accept and register websocket. Closes old connection if any."""
        old = self._connections.get(user_id)
        if old is not None:
            try:
                await old.close(code=1001)
            except Exception:
                pass

        await ws.accept()
        self._connections[user_id] = ws
        logger.debug(
            "WS connected: user_id=%s  total=%s", user_id, len(self._connections)
        )

    def disconnect(self, user_id: int) -> None:
        """Remove user from the registry (does NOT close the socket)."""
        self._connections.pop(user_id, None)
        logger.debug(
            "WS disconnected: user_id=%s  total=%s", user_id, len(self._connections)
        )

    # ------------------------------------------------------------------ #
    #  send helpers                                                        #
    # ------------------------------------------------------------------ #

    async def send_to(self, user_id: int, payload: dict) -> None:
        """Send JSON to a single user. Silently skips if offline."""
        ws = self._connections.get(user_id)
        if ws is None:
            return
        if ws.client_state != WebSocketState.CONNECTED:
            self.disconnect(user_id)
            return
        try:
            await ws.send_json(payload)
        except Exception as exc:
            logger.warning("send_to user_id=%s failed (%s), removing", user_id, exc)
            self.disconnect(user_id)

    async def send_to_many(self, user_ids: list[int], payload: dict) -> None:
        """Fan-out JSON to multiple users concurrently. Skips offline users."""
        if not user_ids:
            return
        await asyncio.gather(
            *(self.send_to(uid, payload) for uid in user_ids),
            return_exceptions=True,
        )

    # ------------------------------------------------------------------ #
    #  helpers                                                             #
    # ------------------------------------------------------------------ #

    def is_connected(self, user_id: int) -> bool:
        return user_id in self._connections

    @property
    def online_user_ids(self) -> list[int]:
        return list(self._connections.keys())


# Глобальный singleton — импортируется везде
manager = ConnectionManager()
