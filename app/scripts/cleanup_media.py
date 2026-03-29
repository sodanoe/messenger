#!/usr/bin/env python3
"""
Скрипт для очистки старых медиафайлов.
Запускается как фоновая задача каждые 24 часа.
"""
import asyncio
import sys
from pathlib import Path

# Добавляем корень проекта в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.database import AsyncSessionLocal
from app.services.media_service import MediaService


async def cleanup():
    async with AsyncSessionLocal() as db:
        service = MediaService(db)
        deleted = await service.cleanup_old_files()
        print(f"Cleaned up {deleted} old media files")


if __name__ == "__main__":
    asyncio.run(cleanup())
