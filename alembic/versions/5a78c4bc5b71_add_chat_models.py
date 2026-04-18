"""add_chat_models

Revision ID: 5a78c4bc5b71
Revises: 06_indexes
Create Date: 2026-04-18 06:15:57.021064

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5a78c4bc5b71'
down_revision: Union[str, None] = '06_indexes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. CustomEmoji — нет FK зависимостей, создаём первой
    op.create_table(
        "custom_emojis",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("shortcode", sa.String(64), nullable=False),
        sa.Column("file_location", sa.String(256), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_custom_emojis_shortcode", "custom_emojis", ["shortcode"], unique=True
    )

    # 2. Chat — ссылается только на users (уже существует)
    op.create_table(
        "chats",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "type",
            sa.Enum("direct", "group", name="chat_type"),
            nullable=False,
        ),
        sa.Column("name", sa.String(128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by_id"], ["users.id"], ondelete="SET NULL"
        ),
    )

    # 3. ChatMember — ссылается на chats и users
    op.create_table(
        "chat_members",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("chat_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "role",
            sa.Enum("admin", "member", name="chat_role"),
            nullable=False,
            server_default="member",
        ),
        sa.ForeignKeyConstraint(["chat_id"], ["chats.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("chat_id", "user_id", name="uq_chat_member"),
    )
    op.create_index(
        "ix_chat_members_user_id", "chat_members", ["user_id"], unique=False
    )

    # 4. ChatMessage — ссылается на chats, users, media_files, и саму себя
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("chat_id", sa.Integer(), nullable=False),
        sa.Column("sender_id", sa.Integer(), nullable=False),
        sa.Column("content_encrypted", sa.Text(), nullable=False),
        sa.Column("nonce", sa.Text(), nullable=False),
        sa.Column("tag", sa.Text(), nullable=False),
        sa.Column("media_id", sa.Integer(), nullable=True),
        sa.Column("reply_to_id", sa.Integer(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["chat_id"], ["chats.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["media_id"], ["media_files.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["reply_to_id"], ["chat_messages.id"], ondelete="SET NULL"
        ),
    )
    op.create_index(
        "ix_chat_messages_chat_id", "chat_messages", ["chat_id"], unique=False
    )

    # 5. ChatMessageReaction — создаём последней, зависит от chat_messages и custom_emojis
    op.create_table(
        "chat_message_reactions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("emoji", sa.String(10), nullable=False),
        sa.Column("custom_emoji_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["message_id"], ["chat_messages.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["custom_emoji_id"], ["custom_emojis.id"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint(
            "message_id", "user_id", "emoji", name="uq_chat_reaction_per_user"
        ),
    )
    op.create_index(
        "ix_chat_reactions_message_id",
        "chat_message_reactions",
        ["message_id"],
        unique=False,
    )


def downgrade() -> None:
    # Обратный порядок — сначала те что зависят от других
    op.drop_index("ix_chat_reactions_message_id", table_name="chat_message_reactions")
    op.drop_table("chat_message_reactions")

    op.drop_index("ix_chat_messages_chat_id", table_name="chat_messages")
    op.drop_table("chat_messages")

    op.drop_index("ix_chat_members_user_id", table_name="chat_members")
    op.drop_table("chat_members")

    op.drop_table("chats")
    op.drop_table("custom_emojis")

    # Удаляем PostgreSQL enum типы
    op.execute("DROP TYPE IF EXISTS chat_type")
    op.execute("DROP TYPE IF EXISTS chat_role")