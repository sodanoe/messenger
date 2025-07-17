from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    PROJECT_NAME: str
    DESCRIPTION: str
    VERSION: str
    DEBUG: bool
    DATABASE_URL: str
    SECRET_KEY: str

    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if len(v) < 16 and not cls.model_fields["DEBUG"].default:
            raise ValueError("SECRET_KEY must be at least 16 characters in production!")
        return v

    class Config:
        env_file = Path(__file__).parent.parent.parent.parent.parent / ".env"
        env_file_encoding = "utf-8"


settings = Settings()
