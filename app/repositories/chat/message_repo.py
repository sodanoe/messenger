from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, MediaFile
from app.models.chat import ChatMessage


class MessageRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        chat_id: int,
        sender_id: int,
        content_encrypted: str,
        nonce: str,
        tag: str,
        media_id: int | None = None,
        reply_to_id: int | None = None,
    ) -> ChatMessage:
        msg = ChatMessage(
            chat_id=chat_id,
            sender_id=sender_id,
            content_encrypted=content_encrypted,
            nonce=nonce,
            tag=tag,
            media_id=media_id,
            reply_to_id=reply_to_id,
        )
        self.db.add(msg)
        await self.db.flush()
        await self.db.refresh(msg)
        return msg

    async def get_by_id(self, message_id: int) -> ChatMessage | None:
        result = await self.db.execute(
            select(ChatMessage).where(ChatMessage.id == message_id)
        )
        return result.scalar_one_or_none()

    async def get_by_ids(self, message_ids: list[int]) -> list[ChatMessage]:
        if not message_ids:
            return []
        result = await self.db.execute(
            select(ChatMessage).where(
                ChatMessage.id.in_(message_ids), ChatMessage.is_deleted.is_(False)
            )
        )
        return list(result.scalars().all())

    async def get_history(
        self, chat_id: int, cursor: int | None, limit: int = 50
    ) -> list[ChatMessage]:
        q = select(ChatMessage).where(
            ChatMessage.chat_id == chat_id, ChatMessage.is_deleted.is_(False)
        )
        if cursor is not None:
            q = q.where(ChatMessage.id < cursor)
        q = q.order_by(ChatMessage.id.desc()).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def get_history_with_details(
        self, chat_id: int, cursor: int | None, limit: int = 50
    ):
        """Получает историю сообщений со всеми связанными данными за 1 запрос (через JOIN)"""

        # Алиасы для reply-таблиц
        ReplyMessage = ChatMessage.__table__.alias("reply_msg")
        ReplyUser = User.__table__.alias("reply_user")
        ReplyMedia = MediaFile.__table__.alias("reply_media")

        query = (
            select(
                ChatMessage,
                User.username.label("sender_username"),
                MediaFile.path.label("media_path"),
                ReplyMessage.c.id.label("reply_id"),
                ReplyMessage.c.content_encrypted.label("reply_content"),
                ReplyMessage.c.sender_id.label("reply_sender_id"),
                ReplyUser.c.username.label("reply_sender_username"),
                ReplyMedia.c.path.label("reply_media_path"),
            )
            .outerjoin(User, ChatMessage.sender_id == User.id)
            .outerjoin(MediaFile, ChatMessage.media_id == MediaFile.id)
            .outerjoin(ReplyMessage, ChatMessage.reply_to_id == ReplyMessage.c.id)
            .outerjoin(ReplyUser, ReplyMessage.c.sender_id == ReplyUser.c.id)
            .outerjoin(ReplyMedia, ReplyMessage.c.media_id == ReplyMedia.c.id)
            .where(
                ChatMessage.chat_id == chat_id,
                ChatMessage.is_deleted.is_(False),
            )
        )

        if cursor is not None:
            query = query.where(ChatMessage.id < cursor)

        query = query.order_by(ChatMessage.id.desc()).limit(limit)

        result = await self.db.execute(query)
        return result.all()

    async def soft_delete(self, message_id: int) -> None:
        await self.db.execute(
            update(ChatMessage)
            .where(ChatMessage.id == message_id)
            .values(is_deleted=True)
        )

    async def update_content(self, message_id, content_encrypted, nonce, tag) -> None:
        await self.db.execute(
            update(ChatMessage)
            .where(ChatMessage.id == message_id)
            .values(content_encrypted=content_encrypted, nonce=nonce, tag=tag)
        )
