from sqlalchemy import inspect
from sqlalchemy.orm import Session
from src.app.models import Base
import logging

logger = logging.getLogger(__name__)


class DatabaseStatusService:
    @staticmethod
    def get_status(db: Session) -> dict:
        """Возвращает детальный статус БД"""
        inspector = inspect(db.bind)
        existing_tables = inspector.get_table_names()
        all_tables = list(Base.metadata.tables.keys())

        missing_tables = [table for table in all_tables if table not in existing_tables]
        extra_tables = [table for table in existing_tables if table not in all_tables]

        return {
            "tables_count": len(existing_tables),
            "expected_tables": len(all_tables),
            "existing_tables": existing_tables,
            "expected_tables_list": all_tables,
            "missing_tables": missing_tables,
            "extra_tables": extra_tables,
        }
