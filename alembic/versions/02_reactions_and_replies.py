"""add_reactions_and_replies

Revision ID: add_reactions_replies
Revises: add_media_files
Create Date: 2026-03-27
"""

from alembic import op
import sqlalchemy as sa

revision = "02_reactions_and_replies"
down_revision = "01_media_files"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Добавляем reply_to_id в messages (self-referential FK)
    op.add_column(
        "messages",
        sa.Column("reply_to_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_messages_reply_to_id",
        "messages",
        "messages",
        ["reply_to_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Создаём таблицу реакций
    op.create_table(
        "message_reactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("emoji", sa.String(10), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "message_id", "user_id", "emoji", name="uq_reaction_per_user"
        ),
    )
    op.create_index("ix_reactions_message_id", "message_reactions", ["message_id"])


def downgrade() -> None:
    op.drop_index("ix_reactions_message_id", table_name="message_reactions")
    op.drop_table("message_reactions")
    op.drop_constraint("fk_messages_reply_to_id", "messages", type_="foreignkey")
    op.drop_column("messages", "reply_to_id")
