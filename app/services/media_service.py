import asyncio
import uuid
from datetime import datetime, timezone
from pathlib import Path

import aiofiles
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from PIL import Image
import io

from app.core.config import settings
from app.repositories.media_repo import MediaRepository


class MediaService:
    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    ALLOWED_MIMES = {"image/jpeg", "image/png", "image/gif", "image/webp"}

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = MediaRepository(db)
        self.media_dir = Path(settings.MEDIA_DIR)

    async def _get_setting(self, key: str, default: int) -> int:
        """Читает настройку из Redis (overridable admin) или возвращает default."""
        try:
            from app.core.redis_client import get_redis

            redis = get_redis()
            val = await redis.get(f"admin:media:{key}")
            return int(val) if val else default
        except Exception:
            return default

    async def upload(self, user_id: int, file: UploadFile) -> dict:
        """Загрузка и обработка медиафайла"""
        content = await file.read()
        if len(content) > settings.MEDIA_MAX_UPLOAD_MB * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Max {settings.MEDIA_MAX_UPLOAD_MB}MB",
            )

        mime_type = file.content_type or self._guess_mime(content[:1024])
        if mime_type not in self.ALLOWED_MIMES:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Only images (JPEG, PNG, GIF, WebP) are allowed",
            )

        # Получаем настройки до входа в executor (они async)
        max_size = await self._get_setting("max_size", settings.MEDIA_MAX_SIZE)
        colors = await self._get_setting("colors", settings.MEDIA_COLORS)
        quality = await self._get_setting("quality", settings.MEDIA_QUALITY)

        # CPU-heavy Pillow — запускаем в threadpool, не блокируем event loop
        try:
            # FIX: get_event_loop() устарел с Python 3.10, используем get_running_loop()
            loop = asyncio.get_running_loop()
            processed_content, ext = await loop.run_in_executor(
                None,
                self._process_image_sync,
                content,
                mime_type,
                max_size,
                colors,
                quality,
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid image: {str(e)}",
            )

        date_path = datetime.now().strftime("%Y/%m/%d")
        target_dir = self.media_dir / date_path
        target_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{uuid.uuid4().hex}{ext}"
        file_path = target_dir / filename
        relative_path = f"/media/{date_path}/{filename}"

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(processed_content)

        media = await self.repo.create(
            uploader_id=user_id,
            path=relative_path,
            original_name=file.filename or "unknown",
            size=len(processed_content),
        )
        await self.db.commit()

        return {
            "id": media.id,
            "url": relative_path,
            "original_name": media.original_name,
            "size": media.size,
        }

    @staticmethod
    def _process_image_sync(
        content: bytes,
        mime_type: str,
        max_size: int,
        colors: int,
        quality: int,
    ) -> tuple[bytes, str]:
        """Синхронная обработка — вызывается через run_in_executor."""
        img = Image.open(io.BytesIO(content))

        if mime_type == "image/gif":
            output = io.BytesIO()
            img.save(output, format="GIF", save_all=True, optimize=True)
            return output.getvalue(), ".gif"

        if img.mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")

        if max_size and max(img.size) > max_size:
            ratio = max_size / max(img.size)
            new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        # if colors:
        #     img = img.quantize(colors=colors, method=Image.Quantize.MEDIANCUT)
        #     img = img.convert("RGB")

        output = io.BytesIO()
        img.save(
            output, format="JPEG", quality=quality, optimize=True, progressive=True
        )
        return output.getvalue(), ".jpg"

    def _guess_mime(self, header: bytes) -> str:
        """Простое определение MIME по сигнатуре"""
        if header.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        if header.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        if header.startswith(b"GIF87a") or header.startswith(b"GIF89a"):
            return "image/gif"
        if header.startswith(b"RIFF") and b"WEBP" in header[:12]:
            return "image/webp"
        return "application/octet-stream"

    async def cleanup_old_files(self) -> int:
        """Фоновая очистка старых файлов"""
        from datetime import timedelta

        cutoff = datetime.now(timezone.utc) - timedelta(days=settings.MEDIA_TTL_DAYS)
        old_files = await self.repo.delete_old_files(cutoff)
        deleted = 0

        for media in old_files:
            file_path = self.media_dir / media.path[len("/media/") :]
            if file_path.exists():
                file_path.unlink()
            await self.repo.delete_media(media.id)
            deleted += 1

        await self.db.commit()
        return deleted
