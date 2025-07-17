from fastapi import FastAPI
from contextlib import asynccontextmanager
from src.app.core.database.database import create_tables
from src.app.core.config.config import settings
from src.app.routers.user import router as user_router
from src.app.routers.chat import router as chat_router
from src.app.routers.message import router as message_router
from src.app.routers.websocket import router as websocket_router
from src.app.endpoints import root, health, db_status
from fastapi.middleware.cors import CORSMiddleware
from src.app.middleware.error_handlers import internal_server_error_handler
from src.app.middleware.logging_middleware import log_requests_middleware
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутов
app.include_router(user_router)
app.include_router(chat_router)
app.include_router(message_router)
app.include_router(websocket_router)
app.include_router(root.router)
app.include_router(health.router)
app.include_router(db_status.router)

# Обработчик исключений для более красивых ошибок
app.exception_handler(500)(internal_server_error_handler)

# Middleware для логирования запросов
app.middleware("http")(log_requests_middleware)
