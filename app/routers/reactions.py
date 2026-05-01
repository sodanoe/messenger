from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.chat import AddReactionRequest
from app.services.reaction_service import ReactionService

router = APIRouter(prefix="/chats", tags=["reactions"])


def get_reaction_service(db: AsyncSession = Depends(get_db)) -> ReactionService:
    return ReactionService(db)


@router.post(
    "/{chat_id}/messages/{message_id}/reactions",
    status_code=status.HTTP_201_CREATED,
)
async def add_reaction(
    chat_id: int,
    message_id: int,
    body: AddReactionRequest,
    current_user: User = Depends(get_current_user),
    service: ReactionService = Depends(get_reaction_service),
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
    service: ReactionService = Depends(get_reaction_service),
):
    await service.remove_reaction(message_id, current_user.id, emoji)
