from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.chat import Chat, ChatType, ChatMember


class ChatRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self, type: ChatType, name: str | None, created_by_id: int | None
    ) -> Chat:
        chat = Chat(type=type, name=name, created_by_id=created_by_id)
        self.db.add(chat)
        await self.db.flush()
        await self.db.refresh(chat)
        return chat

    async def get_by_id(self, chat_id: int) -> Chat | None:
        result = await self.db.execute(select(Chat).where(Chat.id == chat_id))
        return result.scalar_one_or_none()

    async def get_user_chats(self, user_id: int) -> list[Chat]:
        result = await self.db.execute(
            select(Chat)
            .join(ChatMember, ChatMember.chat_id == Chat.id)
            .where(ChatMember.user_id == user_id)
        )
        return list(result.scalars().all())
