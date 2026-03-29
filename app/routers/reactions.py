from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.reaction_service import ReactionService

router = APIRouter(prefix="/messages", tags=["reactions"])


class ReactRequest(BaseModel):
    emoji: str


@router.post("/{message_id}/react", status_code=200)
async def react_to_message(
    message_id: int,
    body: ReactRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Добавить/убрать реакцию на сообщение (toggle)."""
    return await ReactionService(db).react(message_id, current_user.id, body.emoji)
