from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.chat import ChatMember, ChatRole


class MemberRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add(self, chat_id: int, user_id: int, role: ChatRole) -> ChatMember:
        chat_member = ChatMember(chat_id=chat_id, user_id=user_id, role=role)
        self.db.add(chat_member)
        await self.db.flush()
        await self.db.refresh(chat_member)
        return chat_member

    async def remove(self, chat_id: int, user_id: int) -> None:
        await self.db.execute(
            delete(ChatMember).where(
                ChatMember.chat_id == chat_id,
                ChatMember.user_id == user_id,
            )
        )

    async def get_members(self, chat_id: int) -> list[ChatMember]:
        result = await self.db.execute(
            select(ChatMember).where(ChatMember.chat_id == chat_id)
        )
        return list(result.scalars().all())

    async def is_member(self, chat_id: int, user_id: int) -> bool:
        result = await self.db.execute(
            select(ChatMember).where(
                ChatMember.chat_id == chat_id, ChatMember.user_id == user_id
            )
        )
        return result.scalar_one_or_none() is not None
