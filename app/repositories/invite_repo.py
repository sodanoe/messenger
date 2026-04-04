from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invite_code import InviteCode


class InviteRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_unused(self, code: str) -> InviteCode | None:
        result = await self.db.execute(
            select(InviteCode).where(
                InviteCode.code == code, InviteCode.used_by.is_(None)
            )
        )
        return result.scalar_one_or_none()

    async def create(self, code: str, created_by: int) -> InviteCode:
        invite = InviteCode(code=code, created_by=created_by)
        self.db.add(invite)
        await self.db.flush()
        await self.db.refresh(invite)
        return invite

    async def mark_used(self, invite: InviteCode, user_id: int) -> None:
        from datetime import datetime, timezone

        invite.used_by = user_id
        invite.used_at = datetime.now(timezone.utc)
        await self.db.flush()
