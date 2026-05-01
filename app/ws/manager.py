"""
WebSocket Connection Manager.

thread-safe, coroutine-safe менеджер WebSocket соединений.
"""

import asyncio
import logging
from typing import Dict

from fastapi import WebSocket
from starlette.websockets import WebSocketState, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: Dict[int, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    # ── connect / disconnect ──────────────────────────────────────────

    async def connect(self, user_id: int, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._connections.setdefault(user_id, set()).add(ws)
        logger.debug(
            "WS connected: user_id=%s  sockets=%s  total_users=%s",
            user_id,
            len(self._connections.get(user_id, set())),
            len(self._connections),
        )

    async def disconnect(self, user_id: int, ws: WebSocket) -> None:
        """Безопасное отключение с блокировкой."""
        async with self._lock:
            sockets = self._connections.get(user_id)
            if sockets is None:
                return
            sockets.discard(ws)
            if not sockets:
                del self._connections[user_id]

        # Закрываем сокет вне блокировки
        try:
            if ws.client_state != WebSocketState.DISCONNECTED:
                await ws.close()
        except Exception:
            pass

        logger.debug(
            "WS disconnected: user_id=%s  total_users=%s",
            user_id,
            len(self._connections),
        )

    async def disconnect_all(self, user_id: int) -> None:
        """Отключить все сокеты пользователя."""
        async with self._lock:
            sockets = self._connections.pop(user_id, set())

        for ws in sockets:
            try:
                if ws.client_state != WebSocketState.DISCONNECTED:
                    await ws.close()
            except Exception:
                pass

    # ── send helpers ──────────────────────────────────────────────────

    async def send_to(self, user_id: int, payload: dict) -> bool:
        """
        Send JSON to all sockets of a user.
        Returns True if at least one socket received the message.
        """
        # Получаем копию списка сокетов под блокировкой
        async with self._lock:
            sockets = self._connections.get(user_id, set())
            if not sockets:
                return False
            sockets_copy = list(sockets)

        dead: set[WebSocket] = set()
        sent = False

        for ws in sockets_copy:
            # Проверяем состояние непосредственно перед отправкой
            if ws.client_state != WebSocketState.CONNECTED:
                dead.add(ws)
                continue

            try:
                await ws.send_json(payload)
                sent = True
            except (WebSocketDisconnect, RuntimeError) as exc:
                # WebSocketDisconnect: клиент отключился
                # RuntimeError: "Cannot call 'send' once a close message has been sent"
                logger.debug("send_to user_id=%s socket=%s: %s", user_id, id(ws), exc)
                dead.add(ws)
            except Exception as exc:
                # Неожиданная ошибка — логируем как ошибку
                logger.error(
                    "send_to user_id=%s unexpected error: %s",
                    user_id,
                    exc,
                    exc_info=True,
                )
                dead.add(ws)

        # Очистка мёртвых соединений
        if dead:
            async with self._lock:
                current_sockets = self._connections.get(user_id)
                if current_sockets:
                    current_sockets.difference_update(dead)
                    if not current_sockets:
                        del self._connections[user_id]

        return sent

    async def send_to_many(self, user_ids: list[int], payload: dict) -> None:
        """Send to multiple users with proper error isolation."""
        if not user_ids:
            return

        # Запускаем параллельно, но не даём одному упавшему заданию убить всё
        results = await asyncio.gather(
            *(self.send_to(uid, payload) for uid in user_ids),
            return_exceptions=True,
        )

        # Логируем ошибки, если есть
        for uid, result in zip(user_ids, results):
            if isinstance(result, Exception):
                logger.error("send_to_many failed for user_id=%s: %s", uid, result)

    # ── helpers ───────────────────────────────────────────────────────

    async def is_connected(self, user_id: int) -> bool:
        """Thread-safe проверка онлайн-статуса."""
        async with self._lock:
            return bool(self._connections.get(user_id))

    async def online_user_ids(self) -> list[int]:
        """Thread-safe список онлайн пользователей."""
        async with self._lock:
            return list(self._connections.keys())

    async def get_connection_count(self, user_id: int) -> int:
        """Количество активных соединений пользователя."""
        async with self._lock:
            sockets = self._connections.get(user_id, set())
            return len(sockets)


manager = ConnectionManager()
