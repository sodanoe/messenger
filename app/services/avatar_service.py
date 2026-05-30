import asyncio
import uuid
from pathlib import Path
import logging

import aiofiles
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.avatar import ChatAvatar, UserAvatar
from app.repositories.avatar_repo import ChatAvatarRepo, UserAvatarRepo
from app.services.media_service import MediaService

logger = logging.getLogger(__name__)

# Папка для аватарок — отдельно от обычных медиафайлов
AVATAR_DIR = Path(settings.MEDIA_DIR) / "avatars"

# Аватарки сжимаем сильнее — они маленькие, квадратные
AVATAR_MAX_SIZE = 512  # px
AVATAR_QUALITY = 85
AVATAR_COLORS = 256


class AvatarService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.user_repo = UserAvatarRepo(db)
        self.chat_repo = ChatAvatarRepo(db)

    async def upload_user_avatar(self, user_id: int, file: UploadFile) -> dict:
        return await self._upload(
            repo=self.user_repo,
            owner_id=user_id,
            file=file,
            subfolder="users",
        )

    async def upload_chat_avatar(self, chat_id: int, file: UploadFile) -> dict:
        return await self._upload(
            repo=self.chat_repo,
            owner_id=chat_id,
            file=file,
            subfolder="chats",
        )

    async def get_current_user_avatar(self, user_id: int) -> UserAvatar | None:
        return await self.user_repo.get_current(user_id)

    async def get_current_chat_avatar(self, chat_id: int) -> ChatAvatar | None:
        return await self.chat_repo.get_current(chat_id)

    async def get_user_avatar_history(self, user_id: int) -> list[UserAvatar]:
        return await self.user_repo.get_history(user_id)

    async def get_chat_avatar_history(self, chat_id: int) -> list[ChatAvatar]:
        return await self.chat_repo.get_history(chat_id)

    async def delete_user_avatar(self, avatar_id: int, user_id: int) -> None:
        """Удаляет аватарку если она принадлежит этому юзеру."""
        avatar = await self.user_repo.get_by_id(avatar_id)
        if avatar is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Avatar not found"
            )
        if avatar.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not your avatar"
            )
        await self._delete_file(avatar.path)
        await self.user_repo.delete(avatar_id)
        await self.db.commit()

    async def delete_chat_avatar(self, avatar_id: int, chat_id: int) -> None:
        """Удаляет аватарку чата (проверку прав делает роутер/сервис чата)."""
        avatar = await self.chat_repo.get_by_id(avatar_id)
        if avatar is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Avatar not found"
            )
        if avatar.chat_id != chat_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Wrong chat"
            )
        await self._delete_file(avatar.path)
        await self.chat_repo.delete(avatar_id)
        await self.db.commit()

    # ------------------------------------------------------------------
    # internal
    # ------------------------------------------------------------------

    async def _upload(
        self,
        repo: UserAvatarRepo | ChatAvatarRepo,
        owner_id: int,
        file: UploadFile,
        subfolder: str,
    ) -> dict:
        content = await file.read()

        # Валидация MIME — переиспользуем логику из MediaService
        mime_type = file.content_type or MediaService._guess_mime(
            MediaService, content[:1024]
        )
        if mime_type not in MediaService.ALLOWED_MIMES:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Only images (JPEG, PNG, GIF, WebP, HEIC) are allowed",
            )

        # Сжатие через тот же _process_image_sync из MediaService
        try:
            loop = asyncio.get_running_loop()
            processed_content, ext = await loop.run_in_executor(
                None,
                MediaService._process_image_sync,
                content,
                mime_type,
                AVATAR_MAX_SIZE,
                AVATAR_COLORS,
                AVATAR_QUALITY,
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid image: {e}",
            )

        # Сохраняем в avatars/users/<uuid>.jpg или avatars/chats/<uuid>.jpg
        target_dir = AVATAR_DIR / subfolder
        target_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{uuid.uuid4().hex}{ext}"
        file_path = target_dir / filename
        relative_path = f"/media/avatars/{subfolder}/{filename}"

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(processed_content)

        avatar = await repo.add(
            owner_id=owner_id,
            path=relative_path,
            original_name=file.filename or "avatar",
            size=len(processed_content),
        )
        await self.db.commit()

        return {
            "id": avatar.id,
            "url": relative_path,
            "size": avatar.size,
        }

    async def _delete_file(self, relative_path: str) -> None:
        """Удаляет файл с диска. Ошибки логирует, не бросает."""
        clean = relative_path.replace("/media/", "")
        file_path = Path(settings.MEDIA_DIR) / clean
        try:
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            logger.error(f"Error deleting avatar file {file_path}: {e}")
