from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session
import json
import logging
from src.app.core.database.database import get_db
from src.app.models import User, ChatMember
from src.app.core.websocket import manager, handle_websocket_message
from src.app.routers.auth import verify_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["WebSocket"])


async def get_user_from_token(token: str, db: Session) -> User:
    """Получение пользователя из JWT токена для WebSocket"""
    try:
        token_data = verify_token(token)
        user = db.query(User).filter(User.id == token_data.user_id).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or inactive user",
            )
        return user
    except Exception as e:
        logger.error(f"Error getting user from token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )


@router.websocket("/chat/{token}")
async def websocket_endpoint(
    websocket: WebSocket, token: str, db: Session = Depends(get_db)
):
    """WebSocket эндпоинт для real-time сообщений"""
    try:
        # Аутентификация пользователя
        user = await get_user_from_token(token, db)

        # Подключение пользователя
        await manager.connect(websocket, user.id)

        # Подписка на все чаты пользователя
        user_chats = (
            db.query(ChatMember.chat_id).filter(ChatMember.user_id == user.id).all()
        )

        for chat_member in user_chats:
            manager.subscribe_to_chat(user.id, chat_member.chat_id)

        # Уведомление о подключении
        await manager.broadcast_user_status(user.id, "online")

        # Основной цикл обработки сообщений
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                await handle_websocket_message(websocket, user.id, message)
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await websocket.send_text(
                    json.dumps({"type": "error", "message": "Invalid JSON format"})
                )
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}")
                await websocket.send_text(
                    json.dumps({"type": "error", "message": "Internal server error"})
                )

    except HTTPException:
        await websocket.close(code=4001, reason="Authentication failed")
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        await websocket.close(code=4000, reason="Internal server error")
    finally:
        # Отключение пользователя
        if "user" in locals():
            manager.disconnect(user.id)
            await manager.broadcast_user_status(user.id, "offline")


@router.get("/online-users")
async def get_online_users(db: Session = Depends(get_db)):
    """Получение списка онлайн пользователей с именами"""
    user_ids = manager.get_online_users()
    users = db.query(User.id, User.username).filter(User.id.in_(user_ids)).all()

    return {
        "online_users": [{"id": user.id, "username": user.username} for user in users],
        "total_online": len(users),
    }


@router.get("/chat/{chat_id}/online-users")
async def get_chat_online_users(chat_id: int):
    """Получение списка онлайн пользователей в чате"""
    online_users = manager.get_chat_online_users(chat_id)
    return {
        "chat_id": chat_id,
        "online_users": online_users,
        "total_online": len(online_users),
    }


@router.get("/user/{user_id}/status")
async def get_user_status(user_id: int):
    """Проверка онлайн статуса пользователя"""
    is_online = manager.is_user_online(user_id)
    return {
        "user_id": user_id,
        "status": "online" if is_online else "offline",
        "is_online": is_online,
    }
