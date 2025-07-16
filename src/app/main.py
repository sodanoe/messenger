from fastapi import FastAPI, HTTPException, Depends
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
from sqlalchemy import text
from src.app.database import get_db, create_tables
from src.app.config import settings
import time
import logging
import sys

# Улучшенная настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Starting up...")
    try:
        created_tables = create_tables()

        if created_tables:
            logger.info(f"🚀 Созданы таблицы: {', '.join(created_tables)}")
        else:
            logger.info("🚀 Все таблицы уже существуют")

        logger.info("✅ Application startup completed")
    except Exception as e:
        logger.error(f"❌ Error during startup: {e}")
        raise

    yield

    # Shutdown
    logger.info("🛑 Application is shutting down")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
)


@app.get("/")
async def root():
    """Главная страница API"""
    return {
        "message": "Messenger API is running!",
        "version": settings.VERSION,
        "project": settings.PROJECT_NAME,
    }


@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Проверка здоровья приложения и подключения к БД"""
    try:
        db.execute(text("SELECT 1"))
        db.commit()  # Убедимся, что транзакция закрыта
        return {
            "status": "healthy",
            "database": "connected",
            "version": settings.VERSION,
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Database connection failed",
                "message": str(e) if settings.DEBUG else "Internal server error",
            },
        )


@app.get("/db-status")
async def db_status(db: Session = Depends(get_db)):
    """Детальная информация о состоянии базы данных"""
    try:
        from sqlalchemy import inspect
        from src.app.models import Base

        inspector = inspect(db.bind)
        existing_tables = inspector.get_table_names()
        all_tables = list(Base.metadata.tables.keys())

        missing_tables = [table for table in all_tables if table not in existing_tables]
        extra_tables = [table for table in existing_tables if table not in all_tables]

        return {
            "status": "success",
            "message": "Все таблицы существуют"
            if not missing_tables
            else f"Отсутствуют таблицы: {', '.join(missing_tables)}",
            "tables_count": len(existing_tables),
            "expected_tables": len(all_tables),
            "existing_tables": existing_tables,
            "expected_tables_list": all_tables,
            "missing_tables": missing_tables,
            "extra_tables": extra_tables,
            "database_url": settings.DATABASE_URL.split("@")[1]
            if "@" in settings.DATABASE_URL
            else "hidden"
            # Скрываем пароль
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


# Обработчик исключений для более красивых ошибок
@app.exception_handler(500)
async def internal_server_error_handler(request, exc):
    logger.error(f"Internal server error: {exc}")
    return {
        "error": "Internal server error",
        "message": str(exc) if settings.DEBUG else "Something went wrong",
    }


# Middleware для логирования запросов (опционально)
@app.middleware("http")
async def log_requests(request, call_next):
    start_time = time.time()

    response = await call_next(request)

    process_time = time.time() - start_time
    logger.info(
        f"{request.method}{request.url}-{response.status_code}- {process_time: .3f}s"
    )

    return response
