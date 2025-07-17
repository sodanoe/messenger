from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)


class DatabaseHealthService:
    @staticmethod
    def check_connection(db: Session) -> dict:
        """Проверяет подключение к БД и возвращает статус"""
        try:
            db.execute(text("SELECT 1"))
            db.commit()
            return {"status": "healthy", "database": "connected"}
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            raise
