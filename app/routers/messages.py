from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.message_service import MessageService

router = APIRouter(prefix="/messages", tags=["messages"])


class SendMessageRequest(BaseModel):
    content: str
    media_id: int | None = None
    reply_to_id: int | None = None


@router.get("/{user_id}")
async def get_history(
    user_id: int,
    cursor: int | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await MessageService(db).get_history(current_user.id, user_id, cursor)


@router.post("/{user_id}", status_code=201)
async def send_message(
    user_id: int,
    body: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await MessageService(db).send_message(
        current_user.id, user_id, body.content, body.media_id, body.reply_to_id
    )


@router.post("/{user_id}/read", status_code=204)
async def mark_read(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await MessageService(db).mark_read(current_user.id, user_id)

@router.delete("/{message_id}", status_code=204)
async def delete_message(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await MessageService(db).delete_message(current_user.id, message_id)