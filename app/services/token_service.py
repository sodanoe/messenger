# app/services/token_service.py
import secrets

from fastapi import HTTPException, status

from app.core.jwt import (
    create_access_token,
    decode_refresh_token,
)
from app.services.auth_service import _redis_refresh_key


class TokenService:
    """Redis-only операции с токенами. Не требует DB-сессии."""

    async def refresh(self, refresh_token: str, redis) -> str:
        from jose import JWTError
        try:
            user_id, jti = decode_refresh_token(refresh_token)
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        key = _redis_refresh_key(user_id, jti)
        if not await redis.exists(key):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token revoked",
            )

        return create_access_token(user_id)

    async def logout(self, refresh_token: str, redis) -> None:
        from jose import JWTError
        try:
            user_id, jti = decode_refresh_token(refresh_token)
            key = _redis_refresh_key(user_id, jti)
            await redis.delete(key)
        except JWTError:
            pass

    async def create_ws_ticket(self, user_id: int, redis) -> str:
        ticket = secrets.token_hex(16)
        await redis.set(f"ws:ticket:{ticket}", str(user_id), ex=30)
        return ticket