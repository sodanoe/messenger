from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.chat import Chat, ChatType, ChatMember, ChatMessage


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

    async def get_user_chats_with_details(self, user_id: int):
        # 1. Подзапрос остается таким же
        last_message_id_subquery = (
            select(ChatMessage.id)
            .where(ChatMessage.chat_id == Chat.id)
            .where(ChatMessage.is_deleted.is_(False))
            .order_by(desc(ChatMessage.created_at))
            .limit(1)
            .correlate(Chat)
            .scalar_subquery()
        )

        # 2. В основном запросе добавляем ChatMessage.media_id
        stmt = (
            select(
                Chat,
                ChatMessage.content_encrypted.label("last_msg_content"),
                ChatMessage.created_at.label("last_msg_at"),
                ChatMessage.media_id.label("last_msg_media_id")
            )
            .join(ChatMember, ChatMember.chat_id == Chat.id)
            .outerjoin(ChatMessage, ChatMessage.id == last_message_id_subquery)
            .where(ChatMember.user_id == user_id)
            .order_by(desc(func.coalesce(ChatMessage.created_at, Chat.created_at)))
        )

        result = await self.db.execute(stmt)
        return result.all()

    async def get_user_chats(self, user_id: int) -> list[Chat]:
        result = await self.db.execute(
            select(Chat)
            .join(ChatMember, ChatMember.chat_id == Chat.id)
            .where(ChatMember.user_id == user_id)
        )
        return list(result.scalars().all())
