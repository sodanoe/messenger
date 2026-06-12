import asyncio
import os

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crypto.service import (
    async_encrypt_text,
    async_decrypt_text,
)
from app.models.chat import Chat, ChatMessage, ChatType, CustomEmoji
from app.models.contact import ContactStatus
from app.models.media_file import MediaFile
from app.models.user import User
from app.repositories.chat.chat_repo import ChatRepo
from app.repositories.chat.member_repo import MemberRepo
from app.repositories.chat.message_repo import MessageRepo
from app.repositories.chat.reaction_repo import ReactionRepo
from app.repositories.contact_repo import ContactRepository
from app.repositories.media_repo import MediaRepository
from app.ws.notifier import ChatNotifier


PAGE_SIZE = 50
REPLY_PREVIEW_LEN = 120


class MessageService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.chats = ChatRepo(db)
        self.members = MemberRepo(db)
        self.messages = MessageRepo(db)
        self.reactions = ReactionRepo(db)
        self.contacts = ContactRepository(db)
        self.media = MediaRepository(db)
        self.notifier = ChatNotifier()

    # ── shared helpers (used by send_message AND get_history) ──────────────

    @staticmethod
    def _other_member_id(members, user_id: int) -> int | None:
        """ID собеседника в direct-чате — первый участник, чей user_id
        отличается от переданного. Для group-чатов смысла не имеет,
        но и не используется там."""
        return next((m.user_id for m in members if m.user_id != user_id), None)

    @staticmethod
    async def _decrypt_preview(content_encrypted: str) -> str:
        """Расшифровывает контент и обрезает до REPLY_PREVIEW_LEN —
        используется и для reply_to в send_message, и для reply-превью
        в истории сообщений."""
        text = await async_decrypt_text(content_encrypted)
        return text[:REPLY_PREVIEW_LEN]

    # ── send_message: orchestrator ─────────────────────────────────────

    async def send_message(
        self,
        chat_id: int,
        sender_id: int,
        content: str,
        media_id: int | None = None,
        reply_to_id: int | None = None,
    ) -> dict:
        members, member_ids = await self._require_membership(chat_id, sender_id)
        chat = await self.chats.get_by_id(chat_id)
        orig = await self._validate_reply_target(chat_id, reply_to_id)

        other_id = self._other_member_id(members, sender_id)
        if chat.type == ChatType.direct:
            await self._check_direct_chat_permissions(sender_id, other_id, members)

        encrypted = await async_encrypt_text(content)
        msg = await self.messages.create(
            chat_id=chat_id,
            sender_id=sender_id,
            content_encrypted=encrypted,
            media_id=media_id,
            reply_to_id=reply_to_id,
        )

        sender = await self.db.get(User, sender_id)
        media_map = await self._load_media_map(media_id, orig)
        reply_to_obj = await self._build_reply_payload(orig, media_map)
        media_url = media_map.get(media_id) if media_id else None

        if chat.type == ChatType.direct and other_id:
            await self.contacts.set_unread(other_id, sender_id, True)

        await self.db.commit()

        ws_payload = {
            "type": "new_message",
            "id": msg.id,
            "chat_id": chat_id,
            "sender_id": sender_id,
            "sender_username": sender.username if sender else None,
            "content": content,
            "created_at": msg.created_at.isoformat(),
            "media_url": media_url,
            "reply_to": reply_to_obj,
        }
        await self.notifier.new_message(member_ids, sender_id, ws_payload)

        return {
            "id": msg.id,
            "chat_id": msg.chat_id,
            "sender_id": msg.sender_id,
            "content": content,
            "created_at": msg.created_at,
            "reply_to_id": reply_to_id,
            "reply_to": reply_to_obj,
            "reactions": [],
            "media_url": media_url,
        }

    # ── send_message: steps ─────────────────────────────────────────────

    async def _require_membership(
        self, chat_id: int, sender_id: int
    ) -> tuple[list, list[int]]:
        """Возвращает (members, member_ids) или кидает 403, если sender
        не состоит в чате."""
        members = await self.members.get_members(chat_id)
        member_ids = [m.user_id for m in members]

        if sender_id not in member_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not a member"
            )
        return members, member_ids

    async def _validate_reply_target(
        self, chat_id: int, reply_to_id: int | None
    ) -> ChatMessage | None:
        """Если reply_to_id указан — проверяет, что сообщение существует
        и принадлежит этому же чату. Возвращает оригинал или None."""
        if not reply_to_id:
            return None

        orig = await self.messages.get_by_id(reply_to_id)
        if not orig:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reply message not found",
            )
        if orig.chat_id != chat_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reply target",
            )
        return orig

    async def _check_direct_chat_permissions(
        self, sender_id: int, other_id: int | None, members: list
    ) -> None:
        """Для direct-чата проверяет наличие контакта и отсутствие
        блокировки в обе стороны. Кидает 403/404 при нарушении."""
        if other_id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat member not found",
            )

        contact = await self.contacts.get(sender_id, other_id)
        if not contact:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not in contacts"
            )
        if contact.status == ContactStatus.blocked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Contact is blocked"
            )

        reverse = await self.contacts.get(other_id, sender_id)
        if reverse and reverse.status == ContactStatus.blocked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="You are blocked"
            )

    async def _load_media_map(
        self, media_id: int | None, orig: ChatMessage | None
    ) -> dict[int, str]:
        """Батчем подгружает пути для media_id текущего сообщения и
        media_id оригинала (если это reply на сообщение с медиа)."""
        media_ids_needed: set[int] = set()
        if media_id:
            media_ids_needed.add(media_id)
        if orig and orig.media_id:
            media_ids_needed.add(orig.media_id)

        if not media_ids_needed:
            return {}

        result = await self.db.execute(
            select(MediaFile).where(MediaFile.id.in_(media_ids_needed))
        )
        return {mf.id: mf.path for mf in result.scalars().all()}

    async def _build_reply_payload(
        self, orig: ChatMessage | None, media_map: dict[int, str]
    ) -> dict | None:
        """Собирает превью оригинального сообщения для reply_to в ответе."""
        if not orig:
            return None

        return {
            "id": orig.id,
            "sender_id": orig.sender_id,
            "content": await self._decrypt_preview(orig.content_encrypted),
            "media_url": media_map.get(orig.media_id) if orig.media_id else None,
        }

    # ── get_history: orchestrator ───────────────────────────────────────

    async def get_history(self, chat_id: int, user_id: int, cursor: int | None) -> dict:
        chat = await self._require_history_access(chat_id, user_id)
        await self._maybe_clear_unread(chat, chat_id, user_id)

        rows = await self.messages.get_history_with_details(chat_id, cursor)
        if not rows:
            return {"messages": [], "next_cursor": None}

        next_cursor = rows[-1][0].id if len(rows) == PAGE_SIZE else None

        reactions_by_msg = await self._load_reactions_by_message(rows)
        contents, reply_contents = await self._decrypt_history_rows(rows)
        messages = self._assemble_messages(
            rows, contents, reply_contents, reactions_by_msg
        )

        return {"messages": messages, "next_cursor": next_cursor}

    # ── get_history: steps ──────────────────────────────────────────────

    async def _require_history_access(self, chat_id: int, user_id: int) -> Chat:
        """Проверяет членство и возвращает чат, либо кидает 403."""
        if not await self.members.get_single_member(chat_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not a member"
            )
        return await self.chats.get_by_id(chat_id)

    async def _maybe_clear_unread(self, chat: Chat, chat_id: int, user_id: int) -> None:
        """Сбрасывает has_unread для direct-чата при открытии истории —
        только если флаг реально был выставлен, чтобы не плодить
        лишний UPDATE на каждый GET /messages."""
        if chat.type != ChatType.direct:
            return

        members = await self.members.get_members(chat_id)
        other_id = self._other_member_id(members, user_id)
        if not other_id:
            return

        contact = await self.contacts.get(user_id, other_id)
        if contact and contact.has_unread:
            await self.contacts.set_unread(user_id, other_id, False)
            await self.db.commit()

    async def _load_reactions_by_message(self, rows) -> dict[int, list[dict]]:
        """Грузит реакции для всех сообщений страницы + резолвит ссылки
        на кастомные эмодзи в URL."""
        msg_ids = [row[0].id for row in rows]
        all_reactions = await self.reactions.get_by_messages(msg_ids)

        custom_emoji_ids = [
            r.custom_emoji_id for r in all_reactions if r.custom_emoji_id
        ]
        custom_emoji_map: dict[int, str] = {}

        if custom_emoji_ids:
            ce_result = await self.db.execute(
                select(CustomEmoji).where(CustomEmoji.id.in_(custom_emoji_ids))
            )
            for ce in ce_result.scalars().all():
                custom_emoji_map[ce.id] = (
                    f"/media/emojis/{os.path.basename(ce.file_location)}"
                )

        reactions_by_msg: dict[int, list[dict]] = {}
        for r in all_reactions:
            item = {"emoji": r.emoji, "user_id": r.user_id}
            if r.custom_emoji_id and r.custom_emoji_id in custom_emoji_map:
                item["custom_emoji_url"] = custom_emoji_map[r.custom_emoji_id]
            reactions_by_msg.setdefault(r.message_id, []).append(item)

        return reactions_by_msg

    async def _decrypt_history_rows(self, rows) -> tuple[list[str], list[str]]:
        """Параллельно расшифровывает контент сообщений и превью
        их reply-целей."""
        contents = await asyncio.gather(
            *[async_decrypt_text(row[0].content_encrypted) for row in rows]
        )
        reply_contents = await asyncio.gather(
            *[
                self._decrypt_preview(row.reply_content)
                if row.reply_id
                else asyncio.sleep(0, result="")
                for row in rows
            ]
        )
        return list(contents), list(reply_contents)

    @staticmethod
    def _assemble_messages(
        rows,
        contents: list[str],
        reply_contents: list[str],
        reactions_by_msg: dict[int, list[dict]],
    ) -> list[dict]:
        """Собирает финальный список сообщений из строк JOIN-запроса
        и заранее расшифрованного контента."""
        messages = []
        for i, row in enumerate(rows):
            msg = row[0]

            reply_to_data = None
            if row.reply_id:
                reply_to_data = {
                    "id": row.reply_id,
                    "sender_id": row.reply_sender_id,
                    "sender_username": row.reply_sender_username,
                    "content": reply_contents[i],
                    "media_url": row.reply_media_path,
                }

            messages.append(
                {
                    "id": msg.id,
                    "sender_id": msg.sender_id,
                    "sender_username": row.sender_username,
                    "content": contents[i],
                    "created_at": msg.created_at,
                    "reactions": reactions_by_msg.get(msg.id, []),
                    "reply_to": reply_to_data,
                    "media_url": row.media_path,
                }
            )

        return messages

    # ── delete / edit ─────────────────────────────────────────────────────

    async def delete_message(self, user_id: int, message_id: int) -> None:
        msg = await self.messages.get_by_id(message_id)
        if not msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Сообщение не найдено"
            )

        if msg.sender_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нельзя удалить чужое сообщение",
            )

        if msg.is_deleted:
            # Уже удалено — идемпотентно, повторно не уведомляем.
            return

        await self.messages.soft_delete(msg.id)
        await self.db.commit()

        member_ids = await self.members.get_member_ids(msg.chat_id)

        await self.notifier.message_deleted(member_ids, msg.chat_id, message_id)

    async def edit_message(
        self, user_id: int, message_id: int, new_content: str
    ) -> None:
        msg = await self.messages.get_by_id(message_id)
        if not msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Сообщение не найдено"
            )

        if msg.sender_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нельзя редактировать чужое сообщение",
            )

        if msg.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Сообщение не найдено",
            )

        encrypted = await async_encrypt_text(new_content)

        await self.messages.update_content(msg.id, encrypted)
        await self.db.commit()

        member_ids = await self.members.get_member_ids(msg.chat_id)

        await self.notifier.message_edited(member_ids, message_id)
