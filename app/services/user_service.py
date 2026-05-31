from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.media_file import MediaFile
from app.repositories.avatar_repo import UserAvatarRepo
from app.repositories.user_repo import UserRepository


class UserService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.avatars = UserAvatarRepo(db)

    async def delete_account(self, user_id: int) -> None:
        """
        Удаляет аккаунт пользователя.
        CASCADE автоматически удаляет:
          contacts (оба направления), messages, chat members,
          invite_codes (used_by).
        Медиафайлы и аватарки удаляются с диска до удаления записей из БД.
        """
        media_dir = Path(settings.MEDIA_DIR)

        # Собираем пути медиафайлов
        result = await self.db.execute(
            select(MediaFile).where(MediaFile.uploader_id == user_id)
        )
        user_files = result.scalars().all()
        media_paths = [media_dir / mf.path[len("/media/") :] for mf in user_files]

        # Собираем пути аватарок
        avatars = await self.avatars.get_history(user_id)
        avatar_paths = [media_dir / a.path[len("/media/") :] for a in avatars]

        # Удаляем юзера из БД — CASCADE чистит всё связанное
        user = await self.users.get_by_id(user_id)
        if user:
            await self.db.delete(user)
            await self.db.commit()

        # Физические файлы удаляем ПОСЛЕ успешного commit
        # Если unlink упадёт — сироты подберёт media cleanup задача
        for path in media_paths + avatar_paths:
            if path.exists():
                path.unlink()
