"""group media reactions and replies

Revision ID: 03_group_media_reactions
Revises: 02_reactions_and_replies
Create Date: 2026-04-04
"""

from alembic import op
import sqlalchemy as sa

revision = "03_group_media_reactions"
down_revision = "02_reactions_and_replies"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Новые колонки в group_messages
    op.add_column("group_messages", sa.Column("media_id", sa.Integer(), nullable=True))
    op.add_column(
        "group_messages", sa.Column("reply_to_id", sa.Integer(), nullable=True)
    )

    op.create_foreign_key(
        "fk_group_messages_media_id",
        "group_messages",
        "media_files",
        ["media_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_group_messages_reply_to_id",
        "group_messages",
        "group_messages",
        ["reply_to_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Новая таблица реакций
    op.create_table(
        "group_message_reactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "message_id",
            sa.Integer(),
            sa.ForeignKey("group_messages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("emoji", sa.String(10), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_group_reactions_message_id", "group_message_reactions", ["message_id"]
    )
    op.create_unique_constraint(
        "uq_group_reaction_per_user",
        "group_message_reactions",
        ["message_id", "user_id", "emoji"],
    )


def downgrade() -> None:
    op.drop_table("group_message_reactions")
    op.drop_constraint(
        "fk_group_messages_reply_to_id", "group_messages", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_group_messages_media_id", "group_messages", type_="foreignkey"
    )
    op.drop_column("group_messages", "reply_to_id")
    op.drop_column("group_messages", "media_id")
