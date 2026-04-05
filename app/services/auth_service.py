import secrets
import string

import bcrypt
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jwt import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    REFRESH_TOKEN_EXPIRE_DAYS,
)
from app.repositories.invite_repo import InviteRepository
from app.repositories.user_repo import UserRepository


def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def _verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def _redis_refresh_key(user_id: int, token: str) -> str:
    # Храним по первым 16 символам токена — достаточно для идентификации
    return f"refresh:{user_id}:{token[:16]}"


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.invites = InviteRepository(db)

    def _make_tokens(self, user_id: int) -> tuple[str, str]:
        """Возвращает (access_token, refresh_token)."""
        return create_access_token(user_id), create_refresh_token(user_id)

    async def _store_refresh(self, redis, user_id: int, refresh_token: str) -> None:
        """Сохраняем refresh токен в Redis с TTL."""
        key = _redis_refresh_key(user_id, refresh_token)
        await redis.set(key, "1", ex=REFRESH_TOKEN_EXPIRE_DAYS * 86400)

    async def register(
        self, username: str, password: str, invite_code: str, redis
    ) -> tuple[str, str]:
        invite = await self.invites.get_unused(invite_code)
        if not invite:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or used invite code",
            )

        if await self.users.get_by_username(username):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Username already taken"
            )

        pw_hash = _hash_password(password)
        user = await self.users.create(username, pw_hash)
        await self.invites.mark_used(invite, user.id)
        await self.db.commit()

        access, refresh = self._make_tokens(user.id)
        await self._store_refresh(redis, user.id, refresh)
        return access, refresh

    async def login(self, username: str, password: str, redis) -> tuple[str, str]:
        user = await self.users.get_by_username(username)
        if not user or not _verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
            )

        access, refresh = self._make_tokens(user.id)
        await self._store_refresh(redis, user.id, refresh)
        return access, refresh

    async def refresh(self, refresh_token: str, redis) -> str:
        """Валидирует refresh токен, возвращает новый access токен."""
        from jose import JWTError

        try:
            user_id = decode_refresh_token(refresh_token)
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
            )

        key = _redis_refresh_key(user_id, refresh_token)
        if not await redis.exists(key):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked"
            )

        return create_access_token(user_id)

    async def logout(self, refresh_token: str, redis) -> None:
        """Отзываем refresh токен — логаут настоящий."""
        from jose import JWTError

        try:
            user_id = decode_refresh_token(refresh_token)
            key = _redis_refresh_key(user_id, refresh_token)
            await redis.delete(key)
        except JWTError:
            pass  # уже невалидный — ничего страшного

    async def generate_invite(self, admin_user_id: int) -> dict:
        alphabet = string.ascii_letters + string.digits
        code = "".join(secrets.choice(alphabet) for _ in range(8))
        invite = await self.invites.create(code, admin_user_id)
        await self.db.commit()
        return {"code": invite.code}
