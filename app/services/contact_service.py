from fastapi import HTTPException, status
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contact import Contact, ContactStatus
from app.models.user import User
from app.repositories.contact_repo import ContactRepository
from app.repositories.user_repo import UserRepository


class ContactService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.contacts = ContactRepository(db)
        self.users = UserRepository(db)

    async def list_contacts(self, me: int, redis) -> list[dict]:
        rows = await self.contacts.list_for_user(me)
        if not rows:
            return []

        contact_ids = [c.contact_user_id for c in rows]
        users = {u.id: u for u in await self.users.get_by_ids(contact_ids)}

        # Batch presence check — один pipeline вместо N запросов
        online_ids: set[int] = set()
        if rows:
            pipe = redis.pipeline()
            for c in rows:
                pipe.exists(f"user:online:{c.contact_user_id}")
            presences = await pipe.execute()
            online_ids = {
                c.contact_user_id for c, alive in zip(rows, presences) if alive
            }

        result = []
        for c in rows:
            user = users.get(c.contact_user_id)
            result.append(
                {
                    "id": c.id,
                    "contact_user_id": c.contact_user_id,
                    "username": user.username if user else None,
                    "status": c.status,
                    "has_unread": c.has_unread,
                    "is_online": c.contact_user_id in online_ids,
                    "last_message": None,
                }
            )

        return result

    async def add_contact(self, me: int, username: str) -> dict:
        target = await self.users.get_by_username(username)
        if not target:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        if target.id == me:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot add yourself"
            )

        existing = await self.contacts.get(me, target.id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Already a contact"
            )

        c1, _ = await self.contacts.create_pair(me, target.id)
        await self.db.commit()
        return {"id": c1.id, "contact_user_id": target.id, "username": target.username}

    async def delete_contact(self, me: int, contact_user_id: int) -> None:
        existing = await self.contacts.get(me, contact_user_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found"
            )
        await self.contacts.delete_pair(me, contact_user_id)
        await self.db.commit()

    async def block_contact(self, me: int, contact_user_id: int) -> None:
        existing = await self.contacts.get(me, contact_user_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found"
            )
        await self.contacts.block(me, contact_user_id)
        await self.db.commit()

    async def search_users(self, me: int, q: str) -> list[dict]:
        # Один запрос вместо двух: ищем все заблокированные связи
        # в обе стороны через OR
        blocked_res = await self.db.execute(
            select(
                Contact.contact_user_id,
                Contact.user_id,
            ).where(
                Contact.status == ContactStatus.blocked,
                or_(
                    Contact.user_id == me,
                    Contact.contact_user_id == me,
                ),
            )
        )
        blocked_ids: set[int] = set()
        for row in blocked_res.all():
            # Добавляем того, кто не является нами
            blocked_ids.add(
                row.contact_user_id if row.user_id == me else row.user_id
            )

        result = await self.db.execute(
            select(User).where(
                User.username.ilike(f"%{q}%"),
                User.id != me,
            )
        )
        users = result.scalars().all()
        return [
            {"id": u.id, "username": u.username}
            for u in users
            if u.id not in blocked_ids
        ]
