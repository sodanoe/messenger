from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from app.models.media_file import MediaFile


class MediaRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self, uploader_id: int, path: str, original_name: str, size: int
    ) -> MediaFile:
        media = MediaFile(
            uploader_id=uploader_id,
            path=path,
            original_name=original_name,
            size=size,
        )
        self.db.add(media)
        await self.db.flush()
        await self.db.refresh(media)
        return media

    async def get_by_id(self, media_id: int) -> MediaFile | None:
        result = await self.db.execute(
            select(MediaFile).where(MediaFile.id == media_id)
        )
        return result.scalar_one_or_none()

    async def assign_to_message(self, media_id: int, message_id: int) -> None:
        media = await self.get_by_id(media_id)
        if media:
            media.message_id = message_id
            await self.db.flush()

    async def delete_old_files(self, cutoff: datetime) -> list[MediaFile]:
        result = await self.db.execute(
            select(MediaFile).where(MediaFile.created_at < cutoff)
        )
        return list(result.scalars().all())

    async def delete_media(self, media_id: int) -> None:
        await self.db.execute(delete(MediaFile).where(MediaFile.id == media_id))
