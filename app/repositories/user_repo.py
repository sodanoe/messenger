from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_by_ids(self, user_ids: list[int]) -> list[User]:
        if not user_ids:
            return []
        result = await self.db.execute(select(User).where(User.id.in_(user_ids)))
        return list(result.scalars().all())

    async def create(self, username: str, password_hash: str) -> User:
        user = User(username=username, password_hash=password_hash)
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user
