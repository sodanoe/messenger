"""message read_at

Revision ID: 04_message_read_at
Revises: 03_group_media_reactions
Create Date: 2026-04-05
"""

from alembic import op
import sqlalchemy as sa

revision = "04_message_read_at"
down_revision = "03_group_media_reactions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "messages", sa.Column("read_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("messages", "read_at")
