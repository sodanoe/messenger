"""drop_old_tables

Revision ID: 08_drop_old_tables
Revises: 07_add_chat_models
Create Date: 2026-04-19 09:33:07.876533

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "08_drop_old_tables"
down_revision: Union[str, None] = "07_add_chat_models"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Сначала удаляем FK из messages на media_files
    op.drop_constraint("messages_media_id_fkey", "messages", type_="foreignkey")

    # 2. Удаляем FK из messages на саму себя (reply_to_id)
    op.drop_constraint("fk_messages_reply_to_id", "messages", type_="foreignkey")

    # 3. Обнуляем message_id в media_files
    op.execute("UPDATE media_files SET message_id = NULL WHERE message_id IS NOT NULL")

    # 4. Удаляем старый FK из media_files на messages
    op.drop_constraint("media_files_message_id_fkey", "media_files", type_="foreignkey")

    # 5. Создаём новый FK на chat_messages
    op.create_foreign_key(
        "media_files_chat_message_id_fkey",
        "media_files",
        "chat_messages",
        ["message_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # 6. Удаляем таблицы с реакциями (зависят от messages)
    op.drop_table("group_message_reactions")
    op.drop_table("message_reactions")
    op.drop_table("group_messages")
    op.drop_table("group_members")
    op.drop_table("groups")

    # 7. Теперь можно удалить messages
    op.drop_table("messages")

    # 8. Удаляем enum тип
    op.execute("DROP TYPE IF EXISTS group_role")


def downgrade() -> None:
    pass
