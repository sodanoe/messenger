from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.avatar import ChatAvatar, UserAvatar


class BaseAvatarRepo:
    """
    Базовый репозиторий для аватарок.
    Наследники определяют model и owner_field — вся логика здесь.
    """

    model: type
    owner_field: str

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def add(
        self, owner_id: int, path: str, original_name: str, size: int
    ):
        avatar = self.model(
            **{self.owner_field: owner_id},
            path=path,
            original_name=original_name,
            size=size,
        )
        self.db.add(avatar)
        await self.db.flush()
        await self.db.refresh(avatar)
        return avatar

    async def get_current(self, owner_id: int):
        """Последняя аватарка по created_at."""
        result = await self.db.execute(
            select(self.model)
            .where(getattr(self.model, self.owner_field) == owner_id)
            .order_by(self.model.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_history(self, owner_id: int) -> list:
        """Все аватарки, от новых к старым."""
        result = await self.db.execute(
            select(self.model)
            .where(getattr(self.model, self.owner_field) == owner_id)
            .order_by(self.model.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, avatar_id: int):
        result = await self.db.execute(
            select(self.model).where(self.model.id == avatar_id)
        )
        return result.scalar_one_or_none()

    async def delete(self, avatar_id: int) -> None:
        await self.db.execute(
            delete(self.model).where(self.model.id == avatar_id)
        )


class UserAvatarRepo(BaseAvatarRepo):
    model = UserAvatar
    owner_field = "user_id"


class ChatAvatarRepo(BaseAvatarRepo):
    model = ChatAvatar
    owner_field = "chat_id"
