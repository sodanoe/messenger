from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message


class MessageRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, message_id: int) -> Message | None:
        result = await self.db.execute(
            select(Message).where(Message.id == message_id)
        )
        return result.scalar_one_or_none()

    async def get_by_ids(self, ids: list[int]) -> list[Message]:
        if not ids:
            return []
        result = await self.db.execute(
            select(Message).where(Message.id.in_(ids))
        )
        return list(result.scalars().all())

    async def get_history(
        self,
        me: int,
        other: int,
        cursor: int | None,
        limit: int = 50,
    ) -> list[Message]:
        """Cursor-based pagination: newest first (id DESC)."""
        condition = or_(
            and_(Message.sender_id == me, Message.receiver_id == other),
            and_(Message.sender_id == other, Message.receiver_id == me),
        )
        q = select(Message).where(condition)
        if cursor is not None:
            q = q.where(Message.id < cursor)
        q = q.order_by(Message.id.desc()).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def get_last_between(self, me: int, other: int) -> Message | None:
        condition = or_(
            and_(Message.sender_id == me, Message.receiver_id == other),
            and_(Message.sender_id == other, Message.receiver_id == me),
        )
        result = await self.db.execute(
            select(Message).where(condition).order_by(Message.id.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        sender_id: int,
        receiver_id: int,
        content_encrypted: str,
        media_id: int | None = None,
        reply_to_id: int | None = None,
    ) -> Message:
        msg = Message(
            sender_id=sender_id,
            receiver_id=receiver_id,
            content_encrypted=content_encrypted,
            media_id=media_id,
            reply_to_id=reply_to_id,
        )
        self.db.add(msg)
        await self.db.flush()
        await self.db.refresh(msg)
        return msg

    async def delete(self, message: Message) -> None:
        await self.db.delete(message)
