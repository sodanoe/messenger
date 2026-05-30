from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import MediaFile
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.services.avatar_service import AvatarService
from app.services.contact_service import ContactService

router = APIRouter(prefix="/users", tags=["users"])


def get_avatar_service(db: AsyncSession = Depends(get_db)) -> AvatarService:
    return AvatarService(db)


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
    media_dir = Path(settings.MEDIA_DIR)

    result = await db.execute(
        select(MediaFile).where(MediaFile.uploader_id == current_user.id)
    )
    user_files = result.scalars().all()
    file_paths = [media_dir / mf.path[len("/media/"):] for mf in user_files]

    repo = UserRepository(db)
    user = await repo.get_by_id(current_user.id)
    if user:
        await db.delete(user)
        await db.commit()

    for file_path in file_paths:
        if file_path.exists():
            file_path.unlink()


# ---------------------------------------------------------------------------
# Avatar endpoints
# ---------------------------------------------------------------------------

@router.post("/me/avatar", status_code=status.HTTP_201_CREATED)
async def upload_my_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    service: AvatarService = Depends(get_avatar_service),
):
    return await service.upload_user_avatar(current_user.id, file)


@router.get("/me/avatar")
async def get_my_avatar(
    current_user: User = Depends(get_current_user),
    service: AvatarService = Depends(get_avatar_service),
):
    avatar = await service.get_current_user_avatar(current_user.id)
    if avatar is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No avatar")
    return {"id": avatar.id, "url": avatar.path, "created_at": avatar.created_at}


@router.get("/me/avatar/history")
async def get_my_avatar_history(
    current_user: User = Depends(get_current_user),
    service: AvatarService = Depends(get_avatar_service),
):
    avatars = await service.get_user_avatar_history(current_user.id)
    return [{"id": a.id, "url": a.path, "created_at": a.created_at} for a in avatars]


@router.delete("/me/avatar/{avatar_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_avatar(
    avatar_id: int,
    current_user: User = Depends(get_current_user),
    service: AvatarService = Depends(get_avatar_service),
):
    await service.delete_user_avatar(avatar_id, current_user.id)


@router.get("/{user_id}/avatar")
async def get_user_avatar(
    user_id: int,
    service: AvatarService = Depends(get_avatar_service),
):
    avatar = await service.get_current_user_avatar(user_id)
    if avatar is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No avatar")
    return {"id": avatar.id, "url": avatar.path, "created_at": avatar.created_at}