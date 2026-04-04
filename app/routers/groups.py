from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.group_service import GroupService

router = APIRouter(prefix="/groups", tags=["groups"])


class CreateGroupRequest(BaseModel):
    name: str


class InviteMemberRequest(BaseModel):
    username: str


class SendGroupMessageRequest(BaseModel):
    content: str
    media_id: int | None = None
    reply_to_id: int | None = None


class ReactRequest(BaseModel):
    emoji: str


# ── Group CRUD ───────────────────────────────────────────────

@router.get("")
async def list_groups(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await GroupService(db).list_groups(current_user.id)


@router.post("", status_code=201)
async def create_group(
    body: CreateGroupRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await GroupService(db).create_group(current_user.id, body.name)


@router.delete("/{group_id}", status_code=204)
async def delete_group(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await GroupService(db).delete_group(current_user.id, group_id)


# ── Members ──────────────────────────────────────────────────

@router.get("/{group_id}/members")
async def list_members(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await GroupService(db).list_members(current_user.id, group_id)


@router.post("/{group_id}/invite", status_code=201)
async def invite_member(
    group_id: int,
    body: InviteMemberRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await GroupService(db).invite_member(current_user.id, group_id, body.username)


@router.delete("/{group_id}/members/{user_id}", status_code=204)
async def remove_member(
    group_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await GroupService(db).remove_member(current_user.id, group_id, user_id)


@router.post("/{group_id}/leave", status_code=204)
async def leave_group(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await GroupService(db).leave_group(current_user.id, group_id)


# ── Messages ─────────────────────────────────────────────────

@router.get("/{group_id}/messages")
async def get_messages(
    group_id: int,
    cursor: int | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await GroupService(db).get_messages(current_user.id, group_id, cursor)


@router.post("/{group_id}/messages", status_code=201)
async def send_message(
    group_id: int,
    body: SendGroupMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await GroupService(db).send_message(
        current_user.id, group_id, body.content, body.media_id, body.reply_to_id
    )


# ── Reactions ─────────────────────────────────────────────────

@router.post("/{group_id}/messages/{message_id}/react", status_code=200)
async def react_to_message(
    group_id: int,
    message_id: int,
    body: ReactRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await GroupService(db).react(current_user.id, group_id, message_id, body.emoji)