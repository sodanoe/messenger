from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List
from src.app.core.database.database import get_db
from src.app.models import User, Chat, ChatMember
from src.app.schemas import ChatCreate, ChatResponse, UserResponse
from src.app.routers.auth import get_current_active_user

router = APIRouter(prefix="/chats", tags=["Chats"])


@router.post("/create", response_model=ChatResponse)
async def create_chat(
    chat: ChatCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Создание нового чата"""

    # Создаем чат
    db_chat = Chat(name=chat.name, description=chat.description, is_group=chat.is_group)

    db.add(db_chat)
    db.commit()
    db.refresh(db_chat)

    # Добавляем создателя как администратора чата
    chat_member = ChatMember(user_id=current_user.id, chat_id=db_chat.id, role="owner")

    db.add(chat_member)
    db.commit()

    return db_chat


@router.get("/", response_model=List[ChatResponse])
async def get_user_chats(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """Получение всех чатов пользователя"""

    # Получаем все чаты, в которых состоит пользователь
    user_chats = (
        db.query(Chat)
        .join(ChatMember)
        .filter(ChatMember.user_id == current_user.id)
        .all()
    )

    return user_chats


@router.get("/{chat_id}", response_model=ChatResponse)
async def get_chat(
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Получение информации о чате"""

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

    return chat


@router.post("/{chat_id}/join")
async def join_chat(
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Присоединение к чату"""

    # Проверяем, что чат существует
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Чат не найден"
        )

    # Проверяем, что пользователь не состоит в чате
    existing_member = (
        db.query(ChatMember)
        .filter(
            and_(ChatMember.chat_id == chat_id, ChatMember.user_id == current_user.id)
        )
        .first()
    )

    if existing_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Вы уже состоите в этом чате",
        )

    # Добавляем пользователя в чат
    chat_member = ChatMember(user_id=current_user.id, chat_id=chat_id, role="member")

    db.add(chat_member)
    db.commit()

    return {"message": "Вы успешно присоединились к чату"}


@router.post("/{chat_id}/invite/{user_id}")
async def invite_user_to_chat(
    chat_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Приглашение пользователя в чат"""

    # Проверяем, что чат существует
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Чат не найден"
        )

    # Проверяем, что пользователь которого приглашают существует
    invited_user = db.query(User).filter(User.id == user_id).first()
    if not invited_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден"
        )

    # Проверяем, что текущий пользователь является участником чата
    current_member = (
        db.query(ChatMember)
        .filter(
            and_(ChatMember.chat_id == chat_id, ChatMember.user_id == current_user.id)
        )
        .first()
    )

    if not current_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Вы не состоите в этом чате"
        )

    # Проверяем, что приглашаемый пользователь не состоит в чате
    existing_member = (
        db.query(ChatMember)
        .filter(and_(ChatMember.chat_id == chat_id, ChatMember.user_id == user_id))
        .first()
    )

    if existing_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь уже состоит в этом чате",
        )

    # Добавляем пользователя в чат
    chat_member = ChatMember(user_id=user_id, chat_id=chat_id, role="member")

    db.add(chat_member)
    db.commit()

    return {"message": f"Пользователь {invited_user.username} приглашен в чат"}


@router.delete("/{chat_id}/leave")
async def leave_chat(
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Покидание чата"""

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
            status_code=status.HTTP_400_BAD_REQUEST, detail="Вы не состоите в этом чате"
        )

    # Удаляем пользователя из чата
    db.delete(chat_member)
    db.commit()

    return {"message": "Вы покинули чат"}


@router.get("/{chat_id}/members", response_model=List[UserResponse])
async def get_chat_members(
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Получение участников чата"""

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

    # Получаем участников чата
    members = (
        db.query(User).join(ChatMember).filter(ChatMember.chat_id == chat_id).all()
    )

    return members


@router.delete("/{chat_id}")
async def delete_chat(
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Удаление чата (только для владельца)"""

    # Проверяем, что чат существует
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Чат не найден"
        )

    # Проверяем, что пользователь является владельцем чата
    chat_member = (
        db.query(ChatMember)
        .filter(
            and_(
                ChatMember.chat_id == chat_id,
                ChatMember.user_id == current_user.id,
                ChatMember.role == "owner",
            )
        )
        .first()
    )

    if not chat_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только владелец может удалить чат",
        )

    # Удаляем чат (каскадное удаление удалит также участников и сообщения)
    db.delete(chat)
    db.commit()

    return {"message": "Чат успешно удален"}


@router.post("/{chat_id}/create-private")
async def create_private_chat(
    other_user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Создание приватного чата с другим пользователем"""

    # Проверяем, что пользователь существует
    other_user = db.query(User).filter(User.id == other_user_id).first()
    if not other_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден"
        )

    # Проверяем, что пользователь не создает чат с самим собой
    if current_user.id == other_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя создать чат с самим собой",
        )

    # Проверяем, что приватный чат между этими пользователями не существует
    existing_chat = (
        db.query(Chat)
        .join(ChatMember)
        .filter(
            and_(
                Chat.is_group.is_(False),
                ChatMember.user_id.in_([current_user.id, other_user_id]),
            )
        )
        .group_by(Chat.id)
        .having(db.func.count(ChatMember.user_id) == 2)
        .first()
    )

    if existing_chat:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Приватный чат с этим пользователем уже существует",
        )

    # Создаем приватный чат
    chat_name = f"Чат: {current_user.username} - {other_user.username}"
    db_chat = Chat(
        name=chat_name,
        description=f"Приватный чат между {current_user.username} "
        f"и {other_user.username}",
        is_group=False,
    )

    db.add(db_chat)
    db.commit()
    db.refresh(db_chat)

    # Добавляем обоих пользователей в чат
    members = [
        ChatMember(user_id=current_user.id, chat_id=db_chat.id, role="member"),
        ChatMember(user_id=other_user_id, chat_id=db_chat.id, role="member"),
    ]

    db.add_all(members)
    db.commit()

    return db_chat
