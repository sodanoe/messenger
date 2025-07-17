from src.app.core.config.config import settings


class SystemInfoService:
    @staticmethod
    def get_info() -> dict:
        """Возвращает информацию о системе"""
        return {
            "message": "Messenger API is running!",
            "version": settings.VERSION,
            "project": settings.PROJECT_NAME,
            "endpoints": {
                "auth": "/auth",
                "chats": "/chats",
                "messages": "/messages",
                "websocket": "/ws",
                "docs": "/docs",
                "health": "/health",
            },
        }
