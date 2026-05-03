"""fix_media_files_foreign_key_to_chat_messages

Revision ID: 09_fix_media_files_fk
Revises: 08_drop_old_tables
Create Date: 2026-04-19 12:55:06.281052

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "09_fix_media_files_fk"
down_revision: Union[str, None] = "08_drop_old_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Удаляем старый внешний ключ (если существует)
    op.execute("""
        ALTER TABLE media_files 
        DROP CONSTRAINT IF EXISTS media_files_message_id_fkey
    """)

    # Создаём новый внешний ключ на таблицу chat_messages
    op.create_foreign_key(
        "media_files_message_id_fkey",
        "media_files",
        "chat_messages",
        ["message_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    # Откат: возвращаем как было (на таблицу messages)
    op.drop_constraint("media_files_message_id_fkey", "media_files", type_="foreignkey")
    op.create_foreign_key(
        "media_files_message_id_fkey",
        "media_files",
        "messages",
        ["message_id"],
        ["id"],
        ondelete="SET NULL",
    )
