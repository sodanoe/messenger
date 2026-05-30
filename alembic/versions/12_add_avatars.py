"""add user_avatars and chat_avatars tables

Revision ID: 12_add_avatars
Revises: 11_drop_nonce_tag
Create Date: 2025-01-01 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "12_add_avatars"
down_revision = "11_drop_nonce_tag"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_avatars",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("path", sa.String(512), nullable=False),
        sa.Column("original_name", sa.String(256), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_user_avatars_user_id", "user_avatars", ["user_id"])

    op.create_table(
        "chat_avatars",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "chat_id",
            sa.Integer(),
            sa.ForeignKey("chats.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("path", sa.String(512), nullable=False),
        sa.Column("original_name", sa.String(256), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_chat_avatars_chat_id", "chat_avatars", ["chat_id"])


def downgrade() -> None:
    op.drop_index("ix_chat_avatars_chat_id", table_name="chat_avatars")
    op.drop_table("chat_avatars")
    op.drop_index("ix_user_avatars_user_id", table_name="user_avatars")
    op.drop_table("user_avatars")
