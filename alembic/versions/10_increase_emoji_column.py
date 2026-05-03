"""increase_emoji_column_size

Revision ID: 10_increase_emoji_column
Revises: 09_fix_media_files_fk
Create Date: 2026-04-19 13:32:21.254169

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "10_increase_emoji_column"
down_revision: Union[str, None] = "09_fix_media_files_fk"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "chat_message_reactions",
        "emoji",
        existing_type=sa.String(10),
        type_=sa.String(32),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "chat_message_reactions",
        "emoji",
        existing_type=sa.String(32),
        type_=sa.String(10),
        existing_nullable=False,
    )
