from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List
from src.app.database import get_db
from src.app.models import User, Chat, Message, ChatMember
from src.app.schemas import MessageCreate, MessageResponse
from src.app.auth import get_current_active_user
from src.app.websocket_manager import manager

router = APIRouter(prefix="/messages", tags=["Messages"])


@router.post("/send", response_model=MessageResponse)
async def send_message(
    message: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Отправка сообщения в чат"""

    # Проверяем, что чат существует
    chat = db.query(Chat).filter(Chat.id == message.chat_id).first()
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Чат не найден"
        )

    # Проверяем, что пользователь состоит в чате
    chat_member = (
        db.query(ChatMember)
        .filter(
            and_(
                ChatMember.chat_id == message.chat_id,
                ChatMember.user_id == current_user.id,
            )
        )
        .first()
    )

    if not chat_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Вы не состоите в этом чате"
        )

    # Создаем сообщение
    db_message = Message(
        text=message.text, chat_id=message.chat_id, author_id=current_user.id
    )

    db.add(db_message)
    db.commit()
    db.refresh(db_message)

    # Отправляем WebSocket уведомление
    websocket_message = {
        "type": "new_message",
        "message": {
            "id": db_message.id,
            "text": db_message.text,
            "chat_id": db_message.chat_id,
            "author_id": db_message.author_id,
            "author_username": current_user.username,
            "created_at": db_message.created_at.isoformat(),
            "is_edited": db_message.is_edited,
        },
    }

    await manager.send_message_to_chat(
        message.chat_id, websocket_message, exclude_user=current_user.id
    )

    return db_message


@router.get("/chat/{chat_id}", response_model=List[MessageResponse])
async def get_chat_messages(
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    limit: int = Query(default=50, le=100, ge=1),
    offset: int = Query(default=0, ge=0),
):
    """Получение сообщений из чата"""

    # Проверяем, что чат существует
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Чат не найден"
        )

    # Проверяем, что пользователь состоит в чате
    chat_member = (
        db.query(ChatMember)
        .filter(
            and_(ChatMember.chat_id == chat_id, ChatMember.user_id == current_user.id)
        )
        .first()
    )

    if not chat_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Вы не состоите в этом чате"
        )

    # Получаем сообщения
    messages = (
        db.query(Message)
        .filter(Message.chat_id == chat_id)
        .order_by(Message.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return messages


@router.put("/edit/{message_id}", response_model=MessageResponse)
async def edit_message(
    message_id: int,
    new_text: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Редактирование сообщения"""

    # Находим сообщение
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Сообщение не найдено"
        )

    # Проверяем, что пользователь является автором сообщения
    if message.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Вы можете редактировать только свои сообщения",
        )

    # Обновляем сообщение
    message.text = new_text
    message.is_edited = True

    db.commit()
    db.refresh(message)

    # Отправляем WebSocket уведомление
    websocket_message = {
        "type": "message_edited",
        "message": {
            "id": message.id,
            "text": message.text,
            "chat_id": message.chat_id,
            "author_id": message.author_id,
            "author_username": current_user.username,
            "created_at": message.created_at.isoformat(),
            "updated_at": message.updated_at.isoformat()
            if message.updated_at
            else None,
            "is_edited": message.is_edited,
        },
    }

    await manager.send_message_to_chat(
        message.chat_id, websocket_message, exclude_user=current_user.id
    )

    return message


@router.delete("/delete/{message_id}")
async def delete_message(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Удаление сообщения"""

    # Находим сообщение
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Сообщение не найдено"
        )

    # Проверяем, что пользователь является автором сообщения
    if message.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Вы можете удалять только свои сообщения",
        )

    chat_id = message.chat_id

    # Удаляем сообщение
    db.delete(message)
    db.commit()

    # Отправляем WebSocket уведомление
    websocket_message = {
        "type": "message_deleted",
        "message_id": message_id,
        "chat_id": chat_id,
        "deleted_by": current_user.id,
    }

    await manager.send_message_to_chat(
        chat_id, websocket_message, exclude_user=current_user.id
    )

    return {"message": "Сообщение успешно удалено"}


@router.get("/", response_model=List[MessageResponse])
async def get_all_user_messages(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    limit: int = Query(default=50, le=100, ge=1),
    offset: int = Query(default=0, ge=0),
):
    """Получение всех сообщений пользователя"""

    # Получаем все чаты пользователя
    user_chats = (
        db.query(ChatMember.chat_id)
        .filter(ChatMember.user_id == current_user.id)
        .subquery()
    )

    # Получаем сообщения из всех чатов пользователя
    messages = (
        db.query(Message)
        .filter(Message.chat_id.in_(user_chats))
        .order_by(Message.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return messages
