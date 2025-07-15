from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # База данных
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/messenger_db"

    # JWT настройки
    SECRET_KEY: str = "your-super-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Настройки приложения
    PROJECT_NAME: str = "Messenger API"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "Simple messenger API for learning FastAPI and SQLAlchemy"

    # Настройки для разработки
    DEBUG: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = True


# Создаем экземпляр настроек
settings = Settings()
