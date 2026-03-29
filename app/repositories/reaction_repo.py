from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reaction import MessageReaction


class ReactionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_for_message(self, message_id: int) -> list[MessageReaction]:
        result = await self.db.execute(
            select(MessageReaction).where(MessageReaction.message_id == message_id)
        )
        return list(result.scalars().all())

    async def get_for_messages(self, message_ids: list[int]) -> list[MessageReaction]:
        """Батч-запрос для нескольких сообщений — избегаем N+1."""
        if not message_ids:
            return []
        result = await self.db.execute(
            select(MessageReaction).where(MessageReaction.message_id.in_(message_ids))
        )
        return list(result.scalars().all())

    async def toggle(
        self,
        message_id: int,
        user_id: int,
        emoji: str,
    ) -> tuple[bool, list[MessageReaction]]:
        """
        Переключает реакцию: если есть — удаляет, если нет — добавляет.
        Возвращает (добавлено: bool, актуальный список реакций сообщения).
        """
        existing = await self.db.execute(
            select(MessageReaction).where(
                MessageReaction.message_id == message_id,
                MessageReaction.user_id == user_id,
                MessageReaction.emoji == emoji,
            )
        )
        reaction = existing.scalar_one_or_none()

        if reaction:
            await self.db.delete(reaction)
            added = False
        else:
            self.db.add(MessageReaction(
                message_id=message_id,
                user_id=user_id,
                emoji=emoji,
            ))
            added = True

        await self.db.flush()
        updated = await self.get_for_message(message_id)
        return added, updated
