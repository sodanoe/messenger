from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.chat import AddMemberRequest
from app.services.member_service import MemberService

router = APIRouter(prefix="/chats", tags=["members"])


def get_member_service(db: AsyncSession = Depends(get_db)) -> MemberService:
    return MemberService(db)


@router.get("/{chat_id}/members", status_code=status.HTTP_200_OK)
async def get_members(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    service: MemberService = Depends(get_member_service),
):
    return await service.get_members(chat_id, current_user.id)


@router.post("/{chat_id}/members", status_code=status.HTTP_201_CREATED)
async def add_member(
    chat_id: int,
    body: AddMemberRequest,
    current_user: User = Depends(get_current_user),
    service: MemberService = Depends(get_member_service),
):
    return await service.add_member(chat_id, body.user_id, current_user.id)


@router.delete(
    "/{chat_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_member(
    chat_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    service: MemberService = Depends(get_member_service),
):
    await service.remove_member(chat_id, user_id, current_user.id)
