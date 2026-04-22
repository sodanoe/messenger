from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.chat import ChatType
from app.models.user import User
from app.schemas.chat import (
    CreateDirectChatRequest,
    CreateGroupChatRequest,
    SendMessageRequest,
    EditMessageRequest,
    AddMemberRequest,
    AddReactionRequest,
)
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chats", tags=["chats"])


def get_chat_service(db: AsyncSession = Depends(get_db)) -> ChatService:
    return ChatService(db)


# --- Чаты ---


@router.post("/direct", status_code=status.HTTP_201_CREATED)
async def create_direct_chat(
    body: CreateDirectChatRequest,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    chat = await service.create_direct_chat(current_user.id, body.user_id)
    return {"id": chat.id, "type": chat.type, "created_at": chat.created_at}


@router.post("/group", status_code=status.HTTP_201_CREATED)
async def create_group_chat(
    body: CreateGroupChatRequest,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    group = await service.create_group_chat(body.name, current_user.id, body.member_ids)
    return {
        "id": group.id,
        "type": group.type,
        "name": group.name,
        "created_at": group.created_at,
    }


@router.get("/", status_code=status.HTTP_200_OK)
async def get_user_chats(
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    user_chats = await service.get_user_chats(current_user.id)
    result = []
    for c in user_chats:
        other_user_id = None
        other_username = None
        if c.type == ChatType.direct:
            other_user_id = await service.get_other_member_id(c.id, current_user.id)
            # ChatService.get_username_by_id(user_id) -> str | None
            other_username = await service.get_username_by_id(other_user_id)
        result.append(
            {
                "id": c.id,
                "type": c.type,
                "name": c.name,
                "created_at": c.created_at,
                "other_user_id": other_user_id,
                "other_username": other_username,
            }
        )
    return {"chats": result}


@router.get("/{chat_id}/messages")
async def get_history(
    chat_id: int,
    cursor: int | None = None,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    return await service.get_history(chat_id, current_user.id, cursor)


@router.post("/{chat_id}/messages", status_code=status.HTTP_201_CREATED)
async def send_message(
    chat_id: int,
    body: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    return await service.send_message(
        chat_id, current_user.id, body.content, body.media_id, body.reply_to_id
    )


@router.delete(
    "/{chat_id}/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_message(
    chat_id: int,
    message_id: int,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    await service.delete_message(current_user.id, message_id)


@router.put("/{chat_id}/messages/{message_id}")
async def edit_message(
    chat_id: int,
    message_id: int,
    body: EditMessageRequest,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    await service.edit_message(current_user.id, message_id, body.new_content)
    return {"ok": True}


@router.get("/{chat_id}/members", status_code=status.HTTP_200_OK)
async def get_members(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    """
    Список участников чата (прежде всего для групп).
    ChatService.get_members(chat_id, requester_id) -> list[{"id": int, "username": str}]
    Должен проверять что current_user является участником чата, иначе 403.
    """
    return await service.get_members(chat_id, current_user.id)


@router.post("/{chat_id}/members", status_code=status.HTTP_201_CREATED)
async def add_member(
    chat_id: int,
    body: AddMemberRequest,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    return await service.add_member(chat_id, body.user_id, current_user.id)


@router.delete("/{chat_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    chat_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    await service.remove_member(chat_id, user_id, current_user.id)


@router.post(
    "/{chat_id}/messages/{message_id}/reactions", status_code=status.HTTP_201_CREATED
)
async def add_reaction(
    chat_id: int,
    message_id: int,
    body: AddReactionRequest,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    await service.add_reaction(message_id, current_user.id, body.emoji)
    return {"ok": True}


@router.delete(
    "/{chat_id}/messages/{message_id}/reactions/{emoji}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_reaction(
    chat_id: int,
    message_id: int,
    emoji: str,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    await service.remove_reaction(message_id, current_user.id, emoji)