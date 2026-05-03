"""drop nonce and tag columns from chat_messages

Revision ID: 11_drop_nonce_tag
Revises: 10_increase_emoji_column
Create Date: 2025-01-01 00:00:00.000000

ВАЖНО: перед применением проверь что down_revision — актуальный HEAD:
    alembic heads
Если HEAD отличается от "06_indexes" — поправь down_revision ниже.
"""

import sqlalchemy as sa
from alembic import op

revision = "11_drop_nonce_tag"
down_revision = "10_increase_emoji_column"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # nonce и tag хранили пустые строки ("").
    # Всё зашифрованное содержимое уже в content_encrypted (base64 nonce+ct+tag).
    op.drop_column("chat_messages", "nonce")
    op.drop_column("chat_messages", "tag")


def downgrade() -> None:
    # Восстанавливаем как nullable — исходных значений нет, это нормально.
    op.add_column(
        "chat_messages",
        sa.Column("tag", sa.Text(), nullable=True),
    )
    op.add_column(
        "chat_messages",
        sa.Column("nonce", sa.Text(), nullable=True),
    )
