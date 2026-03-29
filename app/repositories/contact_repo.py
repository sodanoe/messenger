from sqlalchemy import and_, delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contact import Contact, ContactStatus


class ContactRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, user_id: int, contact_user_id: int) -> Contact | None:
        result = await self.db.execute(
            select(Contact).where(
                Contact.user_id == user_id,
                Contact.contact_user_id == contact_user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id_and_owner(self, contact_id: int, user_id: int) -> Contact | None:
        result = await self.db.execute(
            select(Contact).where(
                Contact.id == contact_id,
                Contact.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: int) -> list[Contact]:
        result = await self.db.execute(
            select(Contact).where(Contact.user_id == user_id)
        )
        return list(result.scalars().all())

    async def create_pair(
        self, user_id: int, contact_user_id: int
    ) -> tuple[Contact, Contact]:
        """Insert both directions atomically."""
        c1 = Contact(user_id=user_id, contact_user_id=contact_user_id, status=ContactStatus.accepted)
        c2 = Contact(user_id=contact_user_id, contact_user_id=user_id, status=ContactStatus.accepted)
        self.db.add(c1)
        self.db.add(c2)
        await self.db.flush()
        await self.db.refresh(c1)
        await self.db.refresh(c2)
        return c1, c2

    async def delete_pair(self, user_id: int, contact_user_id: int) -> None:
        await self.db.execute(
            delete(Contact).where(
                or_(
                    and_(Contact.user_id == user_id, Contact.contact_user_id == contact_user_id),
                    and_(Contact.user_id == contact_user_id, Contact.contact_user_id == user_id),
                )
            )
        )

    async def block(self, user_id: int, contact_user_id: int) -> None:
        await self.db.execute(
            update(Contact)
            .where(Contact.user_id == user_id, Contact.contact_user_id == contact_user_id)
            .values(status=ContactStatus.blocked)
        )

    async def set_unread(self, user_id: int, contact_user_id: int, value: bool) -> None:
        await self.db.execute(
            update(Contact)
            .where(Contact.user_id == user_id, Contact.contact_user_id == contact_user_id)
            .values(has_unread=value)
        )
