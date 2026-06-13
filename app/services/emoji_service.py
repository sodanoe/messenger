import asyncio
import io
import os
import uuid

from fastapi import HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.emoji_repo import EmojiRepo

EMOJI_DIR = "/app/media/emojis"
MAX_SIZE = 512 * 1024  # 512 KB

# Расширение ВСЕГДА берётся отсюда по провалидированному content_type,
# НИКОГДА из file.filename (контролируется клиентом). Иначе StaticFiles
# отдаёт файл с Content-Type по расширению (.svg -> image/svg+xml,
# .html -> text/html), и встроенный <script> исполняется в origin'е
# приложения при прямой навигации на /media/emojis/....
ALLOWED_MIME_EXT = {
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
    "image/jpeg": "jpg",
}


def _write_file(path: str, data: bytes) -> None:
    with open(path, "wb") as f:
        f.write(data)


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
        shortcode = shortcode.strip().strip(":")
        if not shortcode or not shortcode.replace("_", "").isalnum():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Shortcode может содержать только буквы, цифры и _",
            )

        if file.content_type not in ALLOWED_MIME_EXT:
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

        # Проверяем, что это РЕАЛЬНО декодируемое изображение нужного
        # формата — отсекает SVG/HTML/произвольные байты с подделанным
        # Content-Type (PIL не умеет декодировать SVG/HTML).
        try:
            img = Image.open(io.BytesIO(data))
            img.verify()
        except (UnidentifiedImageError, Exception):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Файл повреждён или не является изображением",
            )

        existing = await self.repo.get_by_shortcode(shortcode)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Эмодзи :{shortcode}: уже существует",
            )

        os.makedirs(EMOJI_DIR, exist_ok=True)
        ext = ALLOWED_MIME_EXT[file.content_type]
        filename = f"{shortcode}_{uuid.uuid4().hex[:8]}.{ext}"
        filepath = os.path.join(EMOJI_DIR, filename)
        await asyncio.to_thread(_write_file, filepath, data)

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

        if os.path.exists(emoji.file_location):
            os.remove(emoji.file_location)

        await self.repo.delete(emoji_id)
        await self.db.commit()

    async def get_by_shortcode(self, shortcode: str):
        return await self.repo.get_by_shortcode(shortcode)
