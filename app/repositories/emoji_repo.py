from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import CustomEmoji


class EmojiRepo:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, shortcode: str, file_location: str) -> CustomEmoji:
        emoji = CustomEmoji(shortcode=shortcode, file_location=file_location)
        self.db.add(emoji)
        await self.db.flush()
        await self.db.refresh(emoji)
        return emoji

    async def get_all(self) -> list[CustomEmoji]:
        result = await self.db.execute(
            select(CustomEmoji).order_by(CustomEmoji.shortcode)
        )
        return list(result.scalars().all())

    async def get_by_id(self, emoji_id: int) -> CustomEmoji | None:
        result = await self.db.execute(
            select(CustomEmoji).where(CustomEmoji.id == emoji_id)
        )
        return result.scalar_one_or_none()

    async def get_by_shortcode(self, shortcode: str) -> CustomEmoji | None:
        result = await self.db.execute(
            select(CustomEmoji).where(CustomEmoji.shortcode == shortcode)
        )
        return result.scalar_one_or_none()

    async def delete(self, emoji_id: int) -> None:
        await self.db.execute(delete(CustomEmoji).where(CustomEmoji.id == emoji_id))
