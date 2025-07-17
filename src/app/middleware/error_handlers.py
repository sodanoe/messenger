from fastapi import Request
from fastapi.responses import JSONResponse
from src.app.core.config.config import settings
import logging

logger = logging.getLogger(__name__)


async def internal_server_error_handler(request: Request, exc: Exception):
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.DEBUG else "Something went wrong",
        },
    )


# Можно добавить другие обработчики, например для 404
async def not_found_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=404,
        content={"error": "Not Found"},
    )
