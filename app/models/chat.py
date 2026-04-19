import enum
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Enum,
    Index,
    Text,
    func,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ChatType(str, enum.Enum):
    direct = "direct"
    group = "group"


class ChatRole(str, enum.Enum):
    admin = "admin"
    member = "member"


class CustomEmoji(Base):
    __tablename__ = "custom_emojis"

    id: Mapped[int] = mapped_column(primary_key=True)
    shortcode: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    file_location: Mapped[str] = mapped_column(String(256), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Chat(Base):
    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[ChatType] = mapped_column(
        Enum(ChatType, name="chat_type"), default=ChatType.direct, nullable=False
    )
    name: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )  # только для групп
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class ChatMember(Base):
    __tablename__ = "chat_members"

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(
        ForeignKey("chats.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[ChatRole] = mapped_column(
        Enum(ChatRole, name="chat_role"), default=ChatRole.member, nullable=False
    )
    __table_args__ = (
        UniqueConstraint("chat_id", "user_id", name="uq_chat_member"),
        Index("ix_chat_members_user_id", "user_id"),
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True)

    chat_id: Mapped[int] = mapped_column(
        ForeignKey("chats.id", ondelete="CASCADE"), nullable=False
    )

    sender_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    content_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    nonce: Mapped[str] = mapped_column(Text, nullable=False)
    tag: Mapped[str] = mapped_column(Text, nullable=False)

    media_id: Mapped[int | None] = mapped_column(
        ForeignKey("media_files.id"),
        nullable=True,
    )

    # Ответ на сообщение (self-referential)
    reply_to_id: Mapped[int | None] = mapped_column(
        ForeignKey("chat_messages.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

    is_deleted: Mapped[bool] = mapped_column(default=False, nullable=False)

    __table_args__ = (Index("ix_chat_messages_chat_id", "chat_id"),)


class ChatMessageReaction(Base):
    __tablename__ = "chat_message_reactions"  # новое имя

    id: Mapped[int] = mapped_column(primary_key=True)

    message_id: Mapped[int] = mapped_column(
        ForeignKey("chat_messages.id", ondelete="CASCADE"),
        nullable=False,  # новая таблица
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    emoji: Mapped[str] = mapped_column(String(32), nullable=False)
    custom_emoji_id: Mapped[int | None] = mapped_column(
        ForeignKey("custom_emojis.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "message_id", "user_id", "emoji", name="uq_chat_reaction_per_user"
        ),
        Index("ix_chat_reactions_message_id", "message_id"),
    )
