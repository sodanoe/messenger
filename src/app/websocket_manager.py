from typing import Dict, List, Set
from fastapi import WebSocket
import json
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Менеджер WebSocket соединений для real-time сообщений"""

    def __init__(self):
        # Активные соединения: {user_id: WebSocket}
        self.active_connections: Dict[int, WebSocket] = {}
        # Подписки на чаты: {chat_id: set(user_ids)}
        self.chat_subscriptions: Dict[int, Set[int]] = {}
        # Пользователи в чатах: {user_id: set(chat_ids)}
        self.user_chats: Dict[int, Set[int]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        """Подключение пользователя"""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(f"User {user_id} connected via WebSocket")

    def disconnect(self, user_id: int):
        """Отключение пользователя"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]

        # Удаляем пользователя из подписок на чаты
        for chat_id in self.user_chats.get(user_id, set()):
            if chat_id in self.chat_subscriptions:
                self.chat_subscriptions[chat_id].discard(user_id)
                if not self.chat_subscriptions[chat_id]:
                    del self.chat_subscriptions[chat_id]

        if user_id in self.user_chats:
            del self.user_chats[user_id]

        logger.info(f"User {user_id} disconnected from WebSocket")

    def subscribe_to_chat(self, user_id: int, chat_id: int):
        """Подписка пользователя на чат"""
        if chat_id not in self.chat_subscriptions:
            self.chat_subscriptions[chat_id] = set()
        self.chat_subscriptions[chat_id].add(user_id)

        if user_id not in self.user_chats:
            self.user_chats[user_id] = set()
        self.user_chats[user_id].add(chat_id)

    def unsubscribe_from_chat(self, user_id: int, chat_id: int):
        """Отписка пользователя от чата"""
        if chat_id in self.chat_subscriptions:
            self.chat_subscriptions[chat_id].discard(user_id)
            if not self.chat_subscriptions[chat_id]:
                del self.chat_subscriptions[chat_id]

        if user_id in self.user_chats:
            self.user_chats[user_id].discard(chat_id)
            if not self.user_chats[user_id]:
                del self.user_chats[user_id]

    async def send_personal_message(self, user_id: int, message: dict):
        """Отправка личного сообщения пользователю"""
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message to user {user_id}: {e}")
                self.disconnect(user_id)

    async def send_message_to_chat(
        self, chat_id: int, message: dict, exclude_user: int = None
    ):
        """Отправка сообщения всем участникам чата"""
        if chat_id in self.chat_subscriptions:
            disconnected_users = []

            for user_id in self.chat_subscriptions[chat_id]:
                if exclude_user and user_id == exclude_user:
                    continue

                if user_id in self.active_connections:
                    try:
                        await self.active_connections[user_id].send_text(
                            json.dumps(message)
                        )
                    except Exception as e:
                        logger.error(
                            f"Error sending message to user {user_id} "
                            f"in chat {chat_id}: {e}"
                        )
                        disconnected_users.append(user_id)

            # Очищаем отключенных пользователей
            for user_id in disconnected_users:
                self.disconnect(user_id)

    async def broadcast_user_status(self, user_id: int, status: str):
        """Уведомление о статусе пользователя (онлайн/оффлайн)"""
        message = {"type": "user_status", "user_id": user_id, "status": status}

        # Отправляем во все чаты пользователя
        for chat_id in self.user_chats.get(user_id, set()):
            await self.send_message_to_chat(chat_id, message, exclude_user=user_id)

    def get_online_users(self) -> List[int]:
        """Получение списка онлайн пользователей"""
        return list(self.active_connections.keys())

    def get_chat_online_users(self, chat_id: int) -> List[int]:
        """Получение списка онлайн пользователей в чате"""
        if chat_id not in self.chat_subscriptions:
            return []

        return [
            user_id
            for user_id in self.chat_subscriptions[chat_id]
            if user_id in self.active_connections
        ]

    def is_user_online(self, user_id: int) -> bool:
        """Проверка онлайн статуса пользователя"""
        return user_id in self.active_connections


# Глобальный менеджер соединений
manager = ConnectionManager()


async def handle_websocket_message(websocket: WebSocket, user_id: int, message: dict):
    """Обработка входящих WebSocket сообщений"""
    message_type = message.get("type")

    if message_type == "subscribe_chat":
        chat_id = message.get("chat_id")
        if chat_id:
            manager.subscribe_to_chat(user_id, chat_id)
            await websocket.send_text(
                json.dumps({"type": "subscribed", "chat_id": chat_id})
            )

    elif message_type == "unsubscribe_chat":
        chat_id = message.get("chat_id")
        if chat_id:
            manager.unsubscribe_from_chat(user_id, chat_id)
            await websocket.send_text(
                json.dumps({"type": "unsubscribed", "chat_id": chat_id})
            )

    elif message_type == "ping":
        await websocket.send_text(json.dumps({"type": "pong"}))

    elif message_type == "private_message":
        to_user_id = message.get("to_user_id")
        text = message.get("text")
        if to_user_id and text:
            await manager.send_personal_message(
                to_user_id,
                {"type": "private_message", "from_user_id": user_id, "text": text},
            )

    elif message_type == "typing":
        chat_id = message.get("chat_id")
        if chat_id:
            typing_message = {
                "type": "typing",
                "user_id": user_id,
                "chat_id": chat_id,
                "is_typing": message.get("is_typing", False),
            }
            await manager.send_message_to_chat(
                chat_id, typing_message, exclude_user=user_id
            )
