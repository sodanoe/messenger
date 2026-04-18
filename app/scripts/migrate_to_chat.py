"""
Скрипт миграции данных из старых таблиц в новые чат-модели.

Что делает:
  - messages                → chats (direct) + chat_messages
  - group + group_messages  → chats (group) + chat_messages
  - group_members           → chat_members
  - message_reactions       → chat_message_reactions
  - group_message_reactions → chat_message_reactions

Идемпотентный — можно запускать несколько раз, дубли не создаются.

Запуск:
  docker exec -it messenger_app_1 python -m app.scripts.migrate_to_chat
"""

import asyncio
import logging
import os

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Заглушка для nonce/tag — старые сообщения не имеют AES-GCM полей
EMPTY_NONCE = ""
EMPTY_TAG = ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def fetch_all(db: AsyncSession, sql: str) -> list[dict]:
    result = await db.execute(text(sql))
    rows = result.fetchall()
    keys = result.keys()
    return [dict(zip(keys, row)) for row in rows]


async def fetch_one(db: AsyncSession, sql: str, params: dict) -> dict | None:
    result = await db.execute(text(sql), params)
    row = result.fetchone()
    if row is None:
        return None
    return dict(zip(result.keys(), row))


# ---------------------------------------------------------------------------
# Step 1: Migrate DM chats (messages → chats + chat_messages)
# ---------------------------------------------------------------------------


async def migrate_direct_messages(db: AsyncSession) -> dict[int, int]:
    """Возвращает маппинг: старый message.id → новый chat_message.id"""
    log.info("=== Migrating direct messages ===")

    pairs = await fetch_all(
        db,
        """
        SELECT DISTINCT
            LEAST(sender_id, receiver_id)    AS user_a,
            GREATEST(sender_id, receiver_id) AS user_b
        FROM messages
    """,
    )
    log.info(f"Found {len(pairs)} unique DM conversations")

    pair_to_chat: dict[tuple, int] = {}

    for pair in pairs:
        user_a, user_b = pair["user_a"], pair["user_b"]
        marker = f"__dm_{user_a}_{user_b}__"

        existing = await fetch_one(
            db,
            """
            SELECT id FROM chats WHERE type = 'direct' AND name = :marker
        """,
            {"marker": marker},
        )

        if existing:
            chat_id = existing["id"]
        else:
            result = await db.execute(
                text("""
                INSERT INTO chats (type, name, created_by_id, created_at)
                VALUES ('direct', :marker, :user_a, NOW())
                RETURNING id
            """),
                {"marker": marker, "user_a": user_a},
            )
            chat_id = result.scalar_one()

            for uid in (user_a, user_b):
                await db.execute(
                    text("""
                    INSERT INTO chat_members (chat_id, user_id, role)
                    VALUES (:chat_id, :user_id, 'member')
                    ON CONFLICT (chat_id, user_id) DO NOTHING
                """),
                    {"chat_id": chat_id, "user_id": uid},
                )

        pair_to_chat[(user_a, user_b)] = chat_id

    await db.flush()

    old_messages = await fetch_all(db, "SELECT * FROM messages ORDER BY id")
    log.info(f"Migrating {len(old_messages)} direct messages")

    old_to_new: dict[int, int] = {}

    for msg in old_messages:
        user_a = min(msg["sender_id"], msg["receiver_id"])
        user_b = max(msg["sender_id"], msg["receiver_id"])
        chat_id = pair_to_chat[(user_a, user_b)]

        existing = await fetch_one(
            db,
            """
            SELECT id FROM chat_messages
            WHERE chat_id = :chat_id
              AND sender_id = :sender_id
              AND created_at = :created_at
              AND content_encrypted = :content
        """,
            {
                "chat_id": chat_id,
                "sender_id": msg["sender_id"],
                "created_at": msg["created_at"],
                "content": msg["content_encrypted"],
            },
        )

        if existing:
            old_to_new[msg["id"]] = existing["id"]
            continue

        result = await db.execute(
            text("""
            INSERT INTO chat_messages
                (chat_id, sender_id, content_encrypted, nonce, tag,
                 media_id, is_deleted, created_at)
            VALUES
                (:chat_id, :sender_id, :content_encrypted, :nonce, :tag,
                 :media_id, false, :created_at)
            RETURNING id
        """),
            {
                "chat_id": chat_id,
                "sender_id": msg["sender_id"],
                "content_encrypted": msg["content_encrypted"],
                "nonce": EMPTY_NONCE,
                "tag": EMPTY_TAG,
                "media_id": msg.get("media_id"),
                "created_at": msg["created_at"],
            },
        )
        old_to_new[msg["id"]] = result.scalar_one()

    await db.flush()
    log.info(f"Direct messages migrated: {len(old_to_new)}")
    return old_to_new


# ---------------------------------------------------------------------------
# Step 2: Migrate group chats
# ---------------------------------------------------------------------------


async def migrate_group_messages(db: AsyncSession) -> dict[int, int]:
    """Возвращает маппинг: старый group_message.id → новый chat_message.id"""
    log.info("=== Migrating group messages ===")

    # Поле называется created_by, не owner_id
    groups = await fetch_all(db, "SELECT * FROM groups")
    log.info(f"Found {len(groups)} groups")

    group_to_chat: dict[int, int] = {}

    for group in groups:
        existing = await fetch_one(
            db,
            """
            SELECT id FROM chats
            WHERE type = 'group' AND name = :name AND created_by_id = :owner
        """,
            {"name": group["name"], "owner": group["created_by"]},
        )

        if existing:
            chat_id = existing["id"]
        else:
            result = await db.execute(
                text("""
                INSERT INTO chats (type, name, created_by_id, created_at)
                VALUES ('group', :name, :owner, :created_at)
                RETURNING id
            """),
                {
                    "name": group["name"],
                    "owner": group["created_by"],
                    "created_at": group["created_at"],
                },
            )
            chat_id = result.scalar_one()

        group_to_chat[group["id"]] = chat_id

        members = await fetch_all(
            db,
            f"""
            SELECT user_id, role FROM group_members WHERE group_id = {group["id"]}
        """,
        )
        for member in members:
            role = "admin" if member["role"] == "admin" else "member"
            await db.execute(
                text("""
                INSERT INTO chat_members (chat_id, user_id, role)
                VALUES (:chat_id, :user_id, :role)
                ON CONFLICT (chat_id, user_id) DO NOTHING
            """),
                {"chat_id": chat_id, "user_id": member["user_id"], "role": role},
            )

    await db.flush()

    group_messages = await fetch_all(db, "SELECT * FROM group_messages ORDER BY id")
    log.info(f"Migrating {len(group_messages)} group messages")

    old_to_new: dict[int, int] = {}

    for msg in group_messages:
        chat_id = group_to_chat.get(msg["group_id"])
        if chat_id is None:
            log.warning(
                f"Group {msg['group_id']} not found, skipping message {msg['id']}"
            )
            continue

        existing = await fetch_one(
            db,
            """
            SELECT id FROM chat_messages
            WHERE chat_id = :chat_id
              AND sender_id = :sender_id
              AND created_at = :created_at
              AND content_encrypted = :content
        """,
            {
                "chat_id": chat_id,
                "sender_id": msg["sender_id"],
                "created_at": msg["created_at"],
                "content": msg["content_encrypted"],
            },
        )

        if existing:
            old_to_new[msg["id"]] = existing["id"]
            continue

        result = await db.execute(
            text("""
            INSERT INTO chat_messages
                (chat_id, sender_id, content_encrypted, nonce, tag,
                 media_id, is_deleted, created_at)
            VALUES
                (:chat_id, :sender_id, :content_encrypted, :nonce, :tag,
                 :media_id, false, :created_at)
            RETURNING id
        """),
            {
                "chat_id": chat_id,
                "sender_id": msg["sender_id"],
                "content_encrypted": msg["content_encrypted"],
                "nonce": EMPTY_NONCE,
                "tag": EMPTY_TAG,
                "media_id": msg.get("media_id"),
                "created_at": msg["created_at"],
            },
        )
        old_to_new[msg["id"]] = result.scalar_one()

    await db.flush()
    log.info(f"Group messages migrated: {len(old_to_new)}")
    return old_to_new


# ---------------------------------------------------------------------------
# Step 3: Migrate reactions
# ---------------------------------------------------------------------------


async def migrate_reactions(
    db: AsyncSession,
    dm_mapping: dict[int, int],
    group_mapping: dict[int, int],
) -> None:
    log.info("=== Migrating reactions ===")

    dm_reactions = await fetch_all(db, "SELECT * FROM message_reactions")
    log.info(f"Found {len(dm_reactions)} DM reactions")

    for r in dm_reactions:
        new_msg_id = dm_mapping.get(r["message_id"])
        if new_msg_id is None:
            log.warning(f"DM message {r['message_id']} not in mapping, skipping")
            continue
        await db.execute(
            text("""
            INSERT INTO chat_message_reactions (message_id, user_id, emoji, created_at)
            VALUES (:message_id, :user_id, :emoji, :created_at)
            ON CONFLICT (message_id, user_id, emoji) DO NOTHING
        """),
            {
                "message_id": new_msg_id,
                "user_id": r["user_id"],
                "emoji": r["emoji"],
                "created_at": r["created_at"],
            },
        )

    group_reactions = await fetch_all(db, "SELECT * FROM group_message_reactions")
    log.info(f"Found {len(group_reactions)} group reactions")

    for r in group_reactions:
        new_msg_id = group_mapping.get(r["message_id"])
        if new_msg_id is None:
            log.warning(f"Group message {r['message_id']} not in mapping, skipping")
            continue
        await db.execute(
            text("""
            INSERT INTO chat_message_reactions (message_id, user_id, emoji, created_at)
            VALUES (:message_id, :user_id, :emoji, :created_at)
            ON CONFLICT (message_id, user_id, emoji) DO NOTHING
        """),
            {
                "message_id": new_msg_id,
                "user_id": r["user_id"],
                "emoji": r["emoji"],
                "created_at": r["created_at"],
            },
        )

    await db.flush()
    log.info("Reactions migrated")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main() -> None:
    log.info("Starting data migration to chat models...")

    async with AsyncSessionLocal() as db:
        async with db.begin():
            dm_mapping = await migrate_direct_messages(db)
            group_mapping = await migrate_group_messages(db)
            await migrate_reactions(db, dm_mapping, group_mapping)

    log.info("Migration complete!")


if __name__ == "__main__":
    asyncio.run(main())
