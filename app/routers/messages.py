from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.chat import EditMessageRequest, SendMessageRequest
from app.services.message_service import MessageService

router = APIRouter(prefix="/chats", tags=["messages"])


def get_message_service(db: AsyncSession = Depends(get_db)) -> MessageService:
    return MessageService(db)


@router.get("/{chat_id}/messages")
async def get_history(
    chat_id: int,
    cursor: int | None = None,
    current_user: User = Depends(get_current_user),
    service: MessageService = Depends(get_message_service),
):
    return await service.get_history(chat_id, current_user.id, cursor)


@router.post("/{chat_id}/messages", status_code=status.HTTP_201_CREATED)
async def send_message(
    chat_id: int,
    body: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    service: MessageService = Depends(get_message_service),
):
    return await service.send_message(
        chat_id, current_user.id, body.content, body.media_id, body.reply_to_id
    )


@router.delete(
    "/{chat_id}/messages/{message_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_message(
    chat_id: int,
    message_id: int,
    current_user: User = Depends(get_current_user),
    service: MessageService = Depends(get_message_service),
):
    await service.delete_message(current_user.id, message_id)


@router.put("/{chat_id}/messages/{message_id}")
async def edit_message(
    chat_id: int,
    message_id: int,
    body: EditMessageRequest,
    current_user: User = Depends(get_current_user),
    service: MessageService = Depends(get_message_service),
):
    await service.edit_message(current_user.id, message_id, body.new_content)
    return {"ok": True}
