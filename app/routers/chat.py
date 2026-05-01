from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.chat import CreateDirectChatRequest, CreateGroupChatRequest
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chats", tags=["chats"])


def get_chat_service(db: AsyncSession = Depends(get_db)) -> ChatService:
    return ChatService(db)


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
    chats = await service.get_user_chats_list(current_user.id)
    return {"chats": chats}


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    await service.delete_chat(chat_id, current_user.id)
