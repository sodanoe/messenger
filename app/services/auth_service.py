import asyncio
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


def _redis_refresh_key(user_id: int, jti: str) -> str:
    return f"refresh:{user_id}:{jti}"


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.invites = InviteRepository(db)

    def _make_tokens(self, user_id: int) -> tuple[str, str]:
        """Возвращает (access_token, refresh_token)."""
        return create_access_token(user_id), create_refresh_token(user_id)

    async def _store_refresh(self, redis, user_id: int, refresh_token: str) -> None:
        from jose import JWTError

        try:
            _, jti = decode_refresh_token(refresh_token)
        except JWTError:
            return
        key = _redis_refresh_key(user_id, jti)
        await redis.set(key, "1", ex=REFRESH_TOKEN_EXPIRE_DAYS * 86400)

    async def check_rate_limit(self, ip: str, redis) -> None:
        """Rate limit: 5 попыток / 60 сек / IP. Бросает 429 при превышении."""
        rate_key = f"login:attempts:{ip}"

        attempts = await redis.incr(rate_key)
        if attempts == 1:
            # Первая попытка — фиксируем окно. Expire больше не трогаем.
            await redis.expire(rate_key, 60)

        if attempts > 5:
            ttl = await redis.ttl(rate_key)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Слишком много попыток. Повторите через {ttl} сек.",
            )

    async def create_ws_ticket(self, user_id: int, redis) -> str:
        """Создаёт одноразовый короткоживущий токен для WS-подключения."""
        ticket = secrets.token_hex(16)
        await redis.set(f"ws:ticket:{ticket}", str(user_id), ex=30)
        return ticket

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

        loop = asyncio.get_running_loop()
        pw_hash = await loop.run_in_executor(None, _hash_password, password)
        user = await self.users.create(username, pw_hash)
        await self.invites.mark_used(invite, user.id)
        await self.db.commit()

        access, refresh = self._make_tokens(user.id)
        await self._store_refresh(redis, user.id, refresh)
        return access, refresh

    async def login(self, username: str, password: str, redis) -> tuple[str, str]:
        user = await self.users.get_by_username(username)
        loop = asyncio.get_running_loop()
        ok = (
            await loop.run_in_executor(
                None, _verify_password, password, user.password_hash
            )
            if user
            else False
        )
        if not user or not ok:
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
            user_id, jti = decode_refresh_token(refresh_token)
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
            )

        key = _redis_refresh_key(user_id, jti)
        if not await redis.exists(key):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked"
            )

        return create_access_token(user_id)

    async def logout(self, refresh_token: str, redis) -> None:
        """Отзываем refresh токен — логаут настоящий."""
        from jose import JWTError

        try:
            user_id, jti = decode_refresh_token(refresh_token)
            key = _redis_refresh_key(user_id, jti)
            await redis.delete(key)
        except JWTError:
            pass

    async def generate_invite(self, admin_user_id: int) -> dict:
        alphabet = string.ascii_letters + string.digits
        code = "".join(secrets.choice(alphabet) for _ in range(8))
        invite = await self.invites.create(code, admin_user_id)
        await self.db.commit()
        return {"code": invite.code}
