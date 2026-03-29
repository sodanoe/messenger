"""
Admin API — настройки медиа (хранятся в Redis, переопределяют config.py).
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.deps import get_admin_user
from app.core.redis_client import get_redis

router = APIRouter(prefix="/admin", tags=["admin"])


class MediaSettings(BaseModel):
    quality:  int | None = Field(None, ge=1,   le=95)
    max_size: int | None = Field(None, ge=64,  le=4096)
    colors:   int | None = Field(None, ge=8,   le=256)


@router.get("/media-settings")
async def get_media_settings(_=Depends(get_admin_user)):
    """Текущие настройки сжатия (Redis override или defaults из config)."""
    redis = get_redis()
    q = await redis.get("admin:media:quality")
    s = await redis.get("admin:media:max_size")
    c = await redis.get("admin:media:colors")
    return {
        "quality":  int(q) if q else settings.MEDIA_QUALITY,
        "max_size": int(s) if s else settings.MEDIA_MAX_SIZE,
        "colors":   int(c) if c else settings.MEDIA_COLORS,
        "ttl_days": settings.MEDIA_TTL_DAYS,
        "max_upload_mb": settings.MEDIA_MAX_UPLOAD_MB,
    }


@router.patch("/media-settings", status_code=204)
async def update_media_settings(body: MediaSettings, _=Depends(get_admin_user)):
    """Обновить настройки сжатия (сохраняются в Redis без перезапуска)."""
    redis = get_redis()
    if body.quality  is not None: await redis.set("admin:media:quality",  body.quality)
    if body.max_size is not None: await redis.set("admin:media:max_size", body.max_size)
    if body.colors   is not None: await redis.set("admin:media:colors",   body.colors)
