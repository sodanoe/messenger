"""
WebSocket Connection Manager.

thread-safe, coroutine-safe менеджер WebSocket соединений.
Использует изолированные In-Memory очереди для каждого сокета для предотвращения потерь.
"""

import asyncio
import logging
from typing import Dict, Set

from fastapi import WebSocket
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)


class SocketWrapper:
    """Обертка над сокетом с изолированной очередью отправки."""

    def __init__(self, ws: WebSocket) -> None:
        self.ws = ws
        # Ограничиваем размер очереди (например, 100 сообщений), чтобы защитить память сервера
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        # Запускаем фоновый воркер, который будет последовательно писать в этот сокет
        self.task: asyncio.Task = asyncio.create_task(self._worker())

    async def _worker(self) -> None:
        try:
            while True:
                payload = await self.queue.get()
                try:
                    # Строго последовательная отправка. Исключена конкуренция за сокет.
                    if self.ws.client_state == WebSocketState.CONNECTED:
                        await self.ws.send_json(payload)
                except Exception as exc:
                    logger.debug(
                        "SocketWrapper worker send error (socket %s): %s",
                        id(self.ws),
                        exc,
                    )
                    break  # При любой ошибке сети ломаем цикл и завершаем воркер
                finally:
                    self.queue.task_done()
        except asyncio.CancelledError:
            pass  # Нормальное завершение при закрытии сокета

    def close(self) -> None:
        """Остановка фонового таска."""
        self.task.cancel()


class ConnectionManager:

    def __init__(self) -> None:
        # Теперь храним Set из SocketWrapper вместо сырых сокетов WebSocket
        self._connections: Dict[int, Set[SocketWrapper]] = {}
        self._lock = asyncio.Lock()

    # ── connect / disconnect ──────────────────────────────────────────

    async def connect(self, user_id: int, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            wrapper = SocketWrapper(ws)
            self._connections.setdefault(user_id, set()).add(wrapper)

        logger.debug(
            "WS connected: user_id=%s  sockets=%s  total_users=%s",
            user_id,
            len(self._connections.get(user_id, set())),
            len(self._connections),
        )

    async def disconnect(self, user_id: int, ws: WebSocket) -> None:
        """Безопасное отключение с блокировкой."""
        async with self._lock:
            wrappers = self._connections.get(user_id)
            if not wrappers:
                return

            # Находим нужную обертку по сырому сокету
            target = next((w for w in wrappers if w.ws == ws), None)
            if target:
                target.close()  # Останавливаем воркер
                wrappers.discard(target)

            if not wrappers:
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
            wrappers = self._connections.pop(user_id, set())

        for w in wrappers:
            w.close()  # Гасим воркер
            try:
                if w.ws.client_state != WebSocketState.DISCONNECTED:
                    await w.ws.close()
            except Exception:
                pass

    # ── send helpers ──────────────────────────────────────────────────

    async def send_to(self, user_id: int, payload: dict) -> bool:
        """
        Отправляет JSON во все сокеты пользователя через очереди.
        Метод мгновенный, он НЕ блокирует вызовы из Redis Pub/Sub Listener.
        """
        async with self._lock:
            wrappers = self._connections.get(user_id, set())
            if not wrappers:
                return False
            wrappers_copy = list(wrappers)

        dead: Set[SocketWrapper] = set()
        sent = False

        for w in wrappers_copy:
            # Если сокет уже мертв на уровне протокола
            if w.ws.client_state != WebSocketState.CONNECTED:
                dead.add(w)
                continue

            try:
                # put_nowait мгновенно кладет сообщение в очередь сокета.
                # Больше никакой uvicorn/fastapi RuntimeError здесь не вылетит.
                w.queue.put_nowait(payload)
                sent = True
            except asyncio.QueueFull:
                # Очередь переполнена (клиент «завис» / backpressure).
                # Удаляем сокет, чтобы не копить мусор в памяти.
                logger.warning(
                    "User %s socket %s queue full. Dropping connection.",
                    user_id,
                    id(w.ws),
                )
                dead.add(w)

        # Очистка мертвых соединений
        if dead:
            async with self._lock:
                current_wrappers = self._connections.get(user_id)
                if current_wrappers:
                    for d in dead:
                        d.close()
                        current_wrappers.discard(d)
                    if not current_wrappers:
                        del self._connections[user_id]

        return sent

    async def send_to_many(self, user_ids: list[int], payload: dict) -> None:
        """Отправка множеству пользователей с изоляцией ошибок."""
        if not user_ids:
            return

        results = await asyncio.gather(
            *(self.send_to(uid, payload) for uid in user_ids),
            return_exceptions=True,
        )

        for uid, result in zip(user_ids, results):
            if isinstance(result, Exception):
                logger.error("send_to_many failed for user_id=%s: %s", uid, result)


manager = ConnectionManager()
