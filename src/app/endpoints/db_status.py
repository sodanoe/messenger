import logging

from fastapi import APIRouter, Depends, HTTPException
from src.app.services.database.status import DatabaseStatusService
from src.app.core.database.database import get_db
from sqlalchemy.orm import Session
from src.app.core.config.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Database"])


@router.get("/db-status")
async def db_status(db: Session = Depends(get_db)):
    """Детальная информация о состоянии базы данных"""
    try:
        status = DatabaseStatusService.get_status(db)
        return {
            "status": "success",
            "message": "Все таблицы существуют"
            if not status["missing_tables"]
            else f"Отсутствуют таблицы: {', '.join(status['missing_tables'])}",
            **status,
            "database_url": settings.DATABASE_URL.split("@")[1]
            if "@" in settings.DATABASE_URL
            else "hidden",
        }
    except Exception as e:
        logger.error(f"DB status check failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to check database status",
                "message": str(e) if settings.DEBUG else "Internal server error",
            },
        )
