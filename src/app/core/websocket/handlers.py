from fastapi import WebSocket
import json
import logging

from src.app.core.websocket import manager

logger = logging.getLogger(__name__)


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
