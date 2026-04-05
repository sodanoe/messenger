"""add unique constraints to contacts and group_members

Revision ID: 05_unique_constraints
Revises: 04_message_read_at
Create Date: 2026-04-05

⚠️  Перед применением убедись, что в таблицах нет дублей.
    Скрипт ниже удаляет их автоматически (оставляет запись с минимальным id).
"""

from alembic import op

revision = "05_unique_constraints"
down_revision = "04_message_read_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Удаляем дубли перед добавлением ограничений
    op.execute("""
        DELETE FROM contacts
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM contacts
            GROUP BY user_id, contact_user_id
        )
    """)
    op.execute("""
        DELETE FROM group_members
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM group_members
            GROUP BY group_id, user_id
        )
    """)

    op.create_unique_constraint(
        "uq_contact_pair", "contacts", ["user_id", "contact_user_id"]
    )
    op.create_unique_constraint(
        "uq_group_member", "group_members", ["group_id", "user_id"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_contact_pair", "contacts", type_="unique")
    op.drop_constraint("uq_group_member", "group_members", type_="unique")
