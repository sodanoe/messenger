from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # JWT
    JWT_SECRET: str
    JWT_EXPIRE_MINUTES: int = 60

    # Crypto
    CRYPTO_BACKEND: str = "aes"          # "aes" | future: "e2e"
    CRYPTO_KEY: str                       # 32-byte hex or base64 secret

    # Admin
    ADMIN_USERNAME: str = "admin"
    # Media

    MEDIA_DIR: str = "/app/media"

    MEDIA_MAX_UPLOAD_MB: int = 20

    MEDIA_STORAGE_LIMIT_MB: int = 2048

    MEDIA_MAX_SIZE: int = 1024

    MEDIA_COLORS: int = 64

    MEDIA_QUALITY: int = 55

    MEDIA_TTL_DAYS: int = 30


    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()  # type: ignore[call-arg]
