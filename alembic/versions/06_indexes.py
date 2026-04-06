"""add performance indexes for messages and group_messages

Revision ID: 06_indexes
Revises: 05_unique_constraints
Create Date: 2026-04-06
"""

from alembic import op

revision = "06_indexes"
down_revision = "05_unique_constraints"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # История DM: основной запрос — выборка переписки между двумя юзерами
    op.create_index(
        "ix_messages_receiver_id",
        "messages",
        ["receiver_id"],
    )
    op.create_index(
        "ix_messages_conversation",
        "messages",
        ["sender_id", "receiver_id", "id"],
    )

    # История группы: основной запрос — выборка сообщений группы по id desc
    op.create_index(
        "ix_group_messages_group_id",
        "group_messages",
        ["group_id", "id"],
    )


def downgrade() -> None:
    op.drop_index("ix_messages_receiver_id", table_name="messages")
    op.drop_index("ix_messages_conversation", table_name="messages")
    op.drop_index("ix_group_messages_group_id", table_name="group_messages")
