import os

from fastapi import APIRouter, Depends, File, Form, UploadFile, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import FileResponse

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.services.emoji_service import EmojiService

router = APIRouter(prefix="/emojis", tags=["emojis"])


def get_service(db: AsyncSession = Depends(get_db)) -> EmojiService:
    return EmojiService(db)


@router.get("/", status_code=status.HTTP_200_OK)
async def list_emojis(
    current_user: User = Depends(get_current_user),
    service: EmojiService = Depends(get_service),
):
    return {"emojis": await service.list_emojis()}


@router.get("/{shortcode}.png")
async def get_emoji_image(shortcode: str, db: AsyncSession = Depends(get_db)):
    """Отдача файла эмодзи по shortcode"""
    service = EmojiService(db)
    emoji = await service.get_by_shortcode(shortcode)

    if not emoji:
        raise HTTPException(status_code=404, detail="Emoji not found")

    if not os.path.exists(emoji.file_location):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        emoji.file_location,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=31536000"},
    )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def upload_emoji(
    shortcode: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    service: EmojiService = Depends(get_service),
):
    return await service.upload(shortcode, file)


@router.delete("/{emoji_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_emoji(
    emoji_id: int,
    current_user: User = Depends(get_current_user),
    service: EmojiService = Depends(get_service),
):
    await service.delete(emoji_id)
