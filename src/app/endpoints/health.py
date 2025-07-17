from fastapi import APIRouter, Depends, HTTPException
from src.app.services.database.health import DatabaseHealthService
from src.app.core.database.database import get_db
from sqlalchemy.orm import Session
from src.app.core.config.config import settings

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Проверка здоровья приложения и подключения к БД"""
    try:
        status = DatabaseHealthService.check_connection(db)
        status["version"] = settings.VERSION
        return status
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Database connection failed",
                "message": str(e) if settings.DEBUG else "Internal server error",
            },
        )
