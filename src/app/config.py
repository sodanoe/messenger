from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    PROJECT_NAME: str
    DESCRIPTION: str
    VERSION: str
    DEBUG: bool
    DATABASE_URL: str
    SECRET_KEY: str

    model_config = {
        "env_file": Path(__file__).parent.parent.parent / ".env",  # Три уровня вверх
        "env_file_encoding": "utf-8",
    }


settings = Settings()
