import os

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crypto.service import (
    async_encrypt_text,
    async_decrypt_text,
)
from app.models.chat import ChatType, CustomEmoji
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

    async def send_message(
        self,
        chat_id: int,
        sender_id: int,
        content: str,
        media_id: int | None = None,
        reply_to_id: int | None = None,
    ) -> dict:
        members = await self.members.get_members(chat_id)
        member_ids = [m.user_id for m in members]

        if sender_id not in member_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not a member"
            )

        chat = await self.chats.get_by_id(chat_id)

        orig = None
        if reply_to_id:
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

        if chat.type == ChatType.direct:
            other_id = next(
                (m.user_id for m in members if m.user_id != sender_id), None
            )
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

        encrypted = await async_encrypt_text(content)

        msg = await self.messages.create(
            chat_id=chat_id,
            sender_id=sender_id,
            content_encrypted=encrypted,
            media_id=media_id,
            reply_to_id=reply_to_id,
        )

        sender = await self.db.get(User, sender_id)

        # --- media batch ---
        media_ids_needed: set[int] = set()
        if media_id:
            media_ids_needed.add(media_id)
        if orig and orig.media_id:
            media_ids_needed.add(orig.media_id)

        media_map: dict[int, str] = {}
        if media_ids_needed:
            result = await self.db.execute(
                select(MediaFile).where(MediaFile.id.in_(media_ids_needed))
            )
            for mf in result.scalars().all():
                media_map[mf.id] = mf.path

        media_url = media_map.get(media_id) if media_id else None

        # --- reply ---
        reply_to_obj = None
        if orig:
            reply_to_obj = {
                "id": orig.id,
                "sender_id": orig.sender_id,
                "content": (await async_decrypt_text(orig.content_encrypted))[:120],
                "media_url": media_map.get(orig.media_id) if orig.media_id else None,
            }

        # --- unread ---
        if chat.type == ChatType.direct:
            other_id = next(
                (m.user_id for m in members if m.user_id != sender_id), None
            )
            if other_id:
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

    async def get_history(self, chat_id: int, user_id: int, cursor: int | None) -> dict:
        # Проверка членства
        if not await self.members.is_member(chat_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not a member"
            )

        chat = await self.chats.get_by_id(chat_id)

        # Сброс unread для direct чатов — только если has_unread == True
        # Избегаем лишнего UPDATE на каждый GET /messages
        if chat.type == ChatType.direct:
            members = await self.members.get_members(chat_id)
            other_id = next((m.user_id for m in members if m.user_id != user_id), None)
            if other_id:
                contact = await self.contacts.get(user_id, other_id)
                if contact and contact.has_unread:
                    await self.contacts.set_unread(user_id, other_id, False)
                    await self.db.commit()

        # Используем новый метод с JOIN
        rows = await self.messages.get_history_with_details(chat_id, cursor)

        if not rows:
            return {"messages": [], "next_cursor": None}

        next_cursor = rows[-1][0].id if len(rows) == PAGE_SIZE else None

        # --- реакции (как в оригинале) ---
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

        # --- сборка ответа ---
        messages = []
        for row in rows:
            msg = row[0]
            sender_username = row.sender_username
            media_path = row.media_path

            # Reply данные
            reply_to_data = None
            if row.reply_id:
                reply_to_data = {
                    "id": row.reply_id,
                    "sender_id": row.reply_sender_id,
                    "sender_username": row.reply_sender_username,
                    "content": (await async_decrypt_text(row.reply_content))[:120],
                    "media_url": row.reply_media_path,
                }

            msg_data = {
                "id": msg.id,
                "sender_id": msg.sender_id,
                "sender_username": sender_username,
                "content": await async_decrypt_text(msg.content_encrypted),
                "created_at": msg.created_at,
                "reactions": reactions_by_msg.get(msg.id, []),
                "reply_to": reply_to_data,
                "media_url": media_path,
            }

            messages.append(msg_data)

        return {"messages": messages, "next_cursor": next_cursor}

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

        await self.messages.soft_delete(msg.id)
        await self.db.commit()

        members = await self.members.get_members(msg.chat_id)
        member_ids = [m.user_id for m in members]

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

        encrypted = await async_encrypt_text(new_content)

        await self.messages.update_content(msg.id, encrypted)
        await self.db.commit()

        members = await self.members.get_members(msg.chat_id)
        member_ids = [m.user_id for m in members]

        await self.notifier.message_edited(member_ids, message_id)
