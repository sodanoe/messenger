from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ChatMessageReaction


class ReactionRepo:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def add(
        self,
        message_id: int,
        user_id: int,
        emoji: str,
        custom_emoji_id: int | None = None,
    ) -> ChatMessageReaction:
        chat_message_reaction = ChatMessageReaction(
            message_id=message_id,
            user_id=user_id,
            emoji=emoji,
            custom_emoji_id=custom_emoji_id,
        )
        self.db.add(chat_message_reaction)
        await self.db.flush()
        await self.db.refresh(chat_message_reaction)
        return chat_message_reaction

    async def remove(self, message_id: int, user_id: int, emoji: str) -> None:
        await self.db.execute(
            delete(ChatMessageReaction).where(
                ChatMessageReaction.message_id == message_id,
                ChatMessageReaction.user_id == user_id,
                ChatMessageReaction.emoji == emoji,
            )
        )

    async def get_by_message(self, message_id: int) -> list[ChatMessageReaction]:
        result = await self.db.execute(
            select(ChatMessageReaction).where(
                ChatMessageReaction.message_id == message_id
            )
        )
        return list(result.scalars().all())

    async def get_by_messages(
        self, message_ids: list[int]
    ) -> list[ChatMessageReaction]:
        if not message_ids:
            return []
        result = await self.db.execute(
            select(ChatMessageReaction).where(
                ChatMessageReaction.message_id.in_(message_ids)
            )
        )
        return list(result.scalars().all())
