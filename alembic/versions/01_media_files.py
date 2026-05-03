"""add_media_files

Revision ID: 01_media_files
Revises:
Create Date: 2026-03-24
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "01_media_files"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Создаем таблицу media_files
    op.create_table(
        "media_files",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uploader_id", sa.Integer(), nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=True),
        sa.Column("path", sa.String(512), nullable=False),
        sa.Column("original_name", sa.String(256), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["uploader_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Добавляем колонку media_id в messages
    op.add_column("messages", sa.Column("media_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_messages_media_id",
        "messages",
        "media_files",
        ["media_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_messages_media_id", "messages", type_="foreignkey")
    op.drop_column("messages", "media_id")
    op.drop_table("media_files")
