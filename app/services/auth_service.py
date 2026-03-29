import secrets
import string

import bcrypt
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jwt import create_access_token
from app.repositories.invite_repo import InviteRepository
from app.repositories.user_repo import UserRepository


def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def _verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.invites = InviteRepository(db)

    async def register(self, username: str, password: str, invite_code: str) -> dict:
        invite = await self.invites.get_unused(invite_code)
        if not invite:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or used invite code")

        if await self.users.get_by_username(username):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken")

        pw_hash = _hash_password(password)
        user = await self.users.create(username, pw_hash)
        await self.invites.mark_used(invite, user.id)
        await self.db.commit()

        token = create_access_token(user.id)
        return {"access_token": token, "token_type": "bearer"}

    async def login(self, username: str, password: str) -> dict:
        user = await self.users.get_by_username(username)
        if not user or not _verify_password(password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        token = create_access_token(user.id)
        return {"access_token": token, "token_type": "bearer"}

    async def generate_invite(self, admin_user_id: int) -> dict:
        alphabet = string.ascii_letters + string.digits
        code = "".join(secrets.choice(alphabet) for _ in range(8))
        invite = await self.invites.create(code, admin_user_id)
        await self.db.commit()
        return {"code": invite.code}
