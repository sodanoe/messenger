from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatRole
from app.models.user import User
from app.repositories.chat.chat_repo import ChatRepo
from app.repositories.chat.member_repo import MemberRepo
from app.ws.notifier import ChatNotifier


class MemberService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.chats = ChatRepo(db)
        self.members = MemberRepo(db)
        self.notifier = ChatNotifier()

    async def get_other_member_id(self, chat_id: int, me: int) -> int:
        members = await self.members.get_members(chat_id)
        for m in members:
            if m.user_id != me:
                return m.user_id
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat member not found",
        )

    async def get_members(self, chat_id: int, requester_id: int) -> dict:
        if not await self.members.is_member(chat_id, requester_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not a member"
            )
        members = await self.members.get_members(chat_id)
        user_ids = [m.user_id for m in members]
        users = await self.db.execute(
            select(User.id, User.username).where(User.id.in_(user_ids))
        )
        username_map = {u.id: u.username for u in users.all()}
        return {
            "members": [
                {
                    "id": m.user_id,
                    "username": username_map.get(m.user_id),
                    "role": m.role,
                }
                for m in members
            ]
        }

    async def add_member(self, chat_id: int, user_id: int, adder_id: int) -> None:
        members = await self.members.get_members(chat_id)
        adder = next((m for m in members if m.user_id == adder_id), None)
        if not adder or adder.role != ChatRole.admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can add members",
            )
        await self.members.add(chat_id, user_id, ChatRole.member)
        await self.db.commit()
        chat = await self.chats.get_by_id(chat_id)
        await self.notifier.member_added(user_id, chat_id, chat.name if chat else None)

    async def remove_member(self, chat_id: int, user_id: int, remover_id: int) -> None:
        if user_id != remover_id:
            members = await self.members.get_members(chat_id)
            remover = next((m for m in members if m.user_id == remover_id), None)
            if not remover or remover.role != ChatRole.admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only admins can remove members",
                )
        chat = await self.chats.get_by_id(chat_id)
        await self.members.remove(chat_id, user_id)
        await self.db.commit()
        await self.notifier.member_removed(
            user_id, chat_id, chat.name if chat else None
        )
