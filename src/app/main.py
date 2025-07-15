from fastapi import FastAPI
from .config import settings
from .database import create_tables


# Создаем приложение FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
    debug=settings.DEBUG,
)


# Создаем таблицы при запуске
@app.on_event("startup")
async def startup_event():
    create_tables()
    print("🚀 Database tables created successfully!")


@app.get("/")
async def root():
    return {
        "message": "Messenger API is running!",
        "version": settings.VERSION,
        "project": settings.PROJECT_NAME,
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "database": "connected", "version": settings.VERSION}
