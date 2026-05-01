from pathlib import Path

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.services.contact_service import ContactService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "last_seen": current_user.last_seen,
    }


@router.get("/search")
async def search_users(
    q: str = Query(min_length=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await ContactService(db).search_users(current_user.id, q)


@router.delete("/me", status_code=204)
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Удалить собственный аккаунт.
    CASCADE автоматически удаляет:
      contacts (оба направления), messages, group_members,
      group_messages, invite_codes (used_by).
    Медиафайлы удаляются с диска до удаления записей из БД.
    WS-соединение закрывается немедленно.
    """
    # media_repo = MediaRepository(db)
    media_dir = Path(settings.MEDIA_DIR)

    # Удаляем физические файлы пользователя с диска
    from sqlalchemy import select
    from app.models.media_file import MediaFile

    result = await db.execute(
        select(MediaFile).where(MediaFile.uploader_id == current_user.id)
    )
    user_files = result.scalars().all()
    # Собираем пути ДО удаления записей (после commit объекты могут быть detached)
    file_paths = [media_dir / mf.path[len("/media/") :] for mf in user_files]

    # Сначала удаляем из БД — CASCADE чистит всё связанное
    repo = UserRepository(db)
    user = await repo.get_by_id(current_user.id)
    if user:
        await db.delete(user)
        await db.commit()

    # Физические файлы удаляем ПОСЛЕ успешного commit
    # Если unlink упадёт — сироты подберёт media cleanup задача
    for file_path in file_paths:
        if file_path.exists():
            file_path.unlink()
