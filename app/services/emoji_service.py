import asyncio
import os
import uuid

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CustomEmoji
from app.repositories.emoji_repo import EmojiRepo

EMOJI_DIR = "/app/media/emojis"
ALLOWED_MIME = {"image/png", "image/gif", "image/webp", "image/jpeg"}
MAX_SIZE = 512 * 1024  # 512 KB


class EmojiService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = EmojiRepo(db)

    async def list_emojis(self) -> list[dict]:
        emojis = await self.repo.get_all()
        return [
            {
                "id": e.id,
                "shortcode": e.shortcode,
                "url": f"/media/emojis/{os.path.basename(e.file_location)}",
            }
            for e in emojis
        ]

    async def upload(self, shortcode: str, file: UploadFile) -> dict:
        # Валидация shortcode
        shortcode = shortcode.strip().strip(":")
        if not shortcode or not shortcode.replace("_", "").isalnum():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Shortcode может содержать только буквы, цифры и _",
            )

        # Валидация файла
        if file.content_type not in ALLOWED_MIME:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Разрешены: png, gif, webp, jpeg",
            )

        data = await file.read()
        if len(data) > MAX_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Файл слишком большой (макс 512KB)",
            )

        # Проверить уникальность shortcode
        existing = await self.repo.get_by_shortcode(shortcode)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Эмодзи :{shortcode}: уже существует",
            )

        # Сохранить файл
        os.makedirs(EMOJI_DIR, exist_ok=True)
        ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "png"
        filename = f"{shortcode}_{uuid.uuid4().hex[:8]}.{ext}"
        filepath = os.path.join(EMOJI_DIR, filename)
        await asyncio.to_thread(lambda: open(filepath, "wb").write(data))

        emoji = await self.repo.create(shortcode=shortcode, file_location=filepath)
        await self.db.commit()

        return {
            "id": emoji.id,
            "shortcode": emoji.shortcode,
            "url": f"/media/emojis/{filename}",
        }

    async def delete(self, emoji_id: int) -> None:
        emoji = await self.repo.get_by_id(emoji_id)
        if not emoji:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Эмодзи не найден"
            )

        # Удалить файл
        if os.path.exists(emoji.file_location):
            os.remove(emoji.file_location)

        await self.repo.delete(emoji_id)
        await self.db.commit()

    async def get_by_shortcode(self, shortcode: str):
        """Получить эмодзи по shortcode"""
        result = await self.db.execute(
            select(CustomEmoji).where(CustomEmoji.shortcode == shortcode)
        )
        return result.scalar_one_or_none()
