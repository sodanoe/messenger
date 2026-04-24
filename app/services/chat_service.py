from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.crypto.service import encrypt_text, decrypt_text
from app.models import User
from app.models.contact import ContactStatus
from app.repositories.chat.chat_repo import ChatRepo
from app.repositories.chat.member_repo import MemberRepo
from app.repositories.chat.message_repo import MessageRepo
from app.repositories.chat.reaction_repo import ReactionRepo
from app.models.chat import ChatType, ChatRole, Chat, CustomEmoji, ChatMember
from app.repositories.contact_repo import ContactRepository
from app.repositories.media_repo import MediaRepository
from app.ws.pubsub import publish, publish_to_many


class ChatService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.chats = ChatRepo(db)
        self.members = MemberRepo(db)
        self.messages = MessageRepo(db)
        self.reactions = ReactionRepo(db)
        self.contacts = ContactRepository(db)
        self.media = MediaRepository(db)

    async def create_direct_chat(self, user_a_id: int, user_b_id: int) -> Chat:
        user_chats = await self.chats.get_user_chats(user_a_id)
        for chat in user_chats:
            if chat.type == ChatType.direct:
                if await self.members.is_member(chat.id, user_b_id):
                    return chat
        chat = await self.chats.create(ChatType.direct, None, user_a_id)
        await self.members.add(chat.id, user_a_id, ChatRole.member)
        await self.members.add(chat.id, user_b_id, ChatRole.member)
        await self.db.commit()
        return chat

    async def create_group_chat(
        self, name: str, creator_id: int, members: list[int]
    ) -> Chat:
        chat = await self.chats.create(ChatType.group, name, creator_id)
        await self.members.add(chat.id, creator_id, ChatRole.admin)
        for member in members:
            await self.members.add(chat.id, member, ChatRole.member)
        await self.db.commit()
        return chat

    async def send_message(
        self,
        chat_id: int,
        sender_id: int,
        content: str,
        media_id: int | None = None,
        reply_to_id: int | None = None,
    ) -> dict:
        # 1. Проверить что sender в чате
        if not await self.members.is_member(chat_id, sender_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not a member"
            )

        # 2. Для DM — дополнительно проверить контакты и блокировки
        chat = await self.chats.get_by_id(chat_id)
        if chat.type == ChatType.direct:
            other_id = await self.get_other_member_id(chat_id, sender_id)
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

        # 3. Зашифровать и сохранить
        encrypted = encrypt_text(content)
        msg = await self.messages.create(
            chat_id=chat_id,
            sender_id=sender_id,
            content_encrypted=encrypted,
            nonce="",
            tag="",
            media_id=media_id,
            reply_to_id=reply_to_id,
        )
        await self.db.commit()

        # 4. WebSocket — уведомить всех участников чата
        members = await self.members.get_members(chat_id)
        sender = await self.db.get(User, sender_id)
        media_url = None
        if media_id:
            media = await self.media.get_by_id(media_id)
            if media:
                media_url = media.path

        ws_payload = {
            "type": "new_message",
            "id": msg.id,
            "chat_id": chat_id,
            "sender_id": sender_id,
            "sender_username": sender.username if sender else None,
            "content": content,
            "created_at": msg.created_at.isoformat(),
            "media_url": media_url,
            "reply_to": reply_to_id,
        }
        for member in members:
            if member.user_id != sender_id:
                await publish(member.user_id, ws_payload)

        return {
            "id": msg.id,
            "chat_id": msg.chat_id,
            "sender_id": msg.sender_id,
            "content": content,
            "created_at": msg.created_at,
            "reply_to_id": reply_to_id,
            "reactions": [],
            "media_url": media_url,
        }

    async def get_other_member_id(self, chat_id: int, me: int) -> int:
        """Вспомогательный метод — найти второго участника DM чата."""
        members = await self.members.get_members(chat_id)
        for m in members:
            if m.user_id != me:
                return m.user_id
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Chat member not found"
        )

    async def get_history(self, chat_id: int, user_id: int, cursor: int | None) -> dict:
        if not await self.members.is_member(chat_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not a member"
            )
        msgs = await self.messages.get_history(chat_id, cursor)
        next_cursor = msgs[-1].id if msgs and len(msgs) == 50 else None

        msg_ids = [m.id for m in msgs]
        all_reactions = await self.reactions.get_by_messages(msg_ids)
        reactions_by_msg: dict[int, list[dict]] = {}

        custom_emoji_ids = [
            r.custom_emoji_id for r in all_reactions if r.custom_emoji_id
        ]
        custom_emoji_map = {}
        if custom_emoji_ids:
            ce_result = await self.db.execute(
                select(CustomEmoji).where(CustomEmoji.id.in_(custom_emoji_ids))
            )
            import os

            for ce in ce_result.scalars().all():
                custom_emoji_map[ce.id] = (
                    f"/media/emojis/{os.path.basename(ce.file_location)}"
                )

        for r in all_reactions:
            data = {"emoji": r.emoji, "user_id": r.user_id}
            if r.custom_emoji_id and r.custom_emoji_id in custom_emoji_map:
                data["custom_emoji_url"] = custom_emoji_map[r.custom_emoji_id]
            reactions_by_msg.setdefault(r.message_id, []).append(data)

        reply_ids = [m.reply_to_id for m in msgs if m.reply_to_id]
        reply_map = {m.id: m for m in await self.messages.get_by_ids(reply_ids)}

        user_ids = {m.sender_id for m in msgs}
        users = await self.db.execute(
            select(User.id, User.username).where(User.id.in_(user_ids))
        )
        username_map = {u.id: u.username for u in users.all()}

        messages = []
        for m in msgs:
            msg_data: dict = {
                "id": m.id,
                "sender_id": m.sender_id,
                "sender_username": username_map.get(m.sender_id),
                "content": decrypt_text(m.content_encrypted),
                "created_at": m.created_at,
                "reactions": reactions_by_msg.get(m.id, []),
                "reply_to": None,
            }

            if m.reply_to_id and m.reply_to_id in reply_map:
                orig = reply_map[m.reply_to_id]
                reply_obj = {
                    "id": orig.id,
                    "sender_id": orig.sender_id,
                    "content": decrypt_text(orig.content_encrypted)[:120],
                }
                if orig.media_id:
                    reply_media = await self.media.get_by_id(orig.media_id)
                    if reply_media:
                        reply_obj["media_url"] = reply_media.path
                msg_data["reply_to"] = reply_obj

            if m.media_id:
                msg_media = await self.media.get_by_id(m.media_id)
                if msg_media:
                    msg_data["media_url"] = msg_media.path

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
        for member in members:
            await publish(
                member.user_id,
                {
                    "type": "message_deleted",
                    "chat_id": msg.chat_id,  # ← ДОБАВИТЬ
                    "message_id": message_id,
                },
            )

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
        new_content = encrypt_text(new_content)
        await self.messages.update_content(msg.id, new_content, "", "")
        await self.db.commit()
        members = await self.members.get_members(msg.chat_id)
        for member in members:
            await publish(
                member.user_id, {"type": "message_edited", "message_id": message_id}
            )

    async def add_member(self, chat_id: int, user_id: int, adder_id: int) -> None:
        members = await self.members.get_members(chat_id)
        adder = next((m for m in members if m.user_id == adder_id), None)
        if not adder or adder.role != ChatRole.admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can add members",
            )
        await self.members.add(chat_id, user_id, ChatRole.member)
        await self.db.commit()

    async def remove_member(self, chat_id: int, user_id: int, remover_id: int) -> None:
        if user_id != remover_id:
            members = await self.members.get_members(chat_id)
            remover = next((m for m in members if m.user_id == remover_id), None)
            if not remover or remover.role != ChatRole.admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only admins can remove members",
                )
        await self.members.remove(chat_id, user_id)
        await self.db.commit()

    async def add_reaction(self, message_id: int, user_id: int, emoji: str) -> None:
        msg = await self.messages.get_by_id(message_id)
        if not msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Message not found"
            )
        if not await self.members.is_member(msg.chat_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not a member"
            )

        custom_emoji_id = None
        if emoji.startswith(":") and emoji.endswith(":"):
            shortcode = emoji[1:-1]
            result = await self.db.execute(
                select(CustomEmoji).where(CustomEmoji.shortcode == shortcode)
            )
            custom_emoji = result.scalar_one_or_none()
            if custom_emoji:
                custom_emoji_id = custom_emoji.id

        try:
            await self.reactions.add(msg.id, user_id, emoji, custom_emoji_id)
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            return

        members = await self.members.get_members(msg.chat_id)
        member_ids = [m.user_id for m in members]
        reactions = await self.reactions.get_by_message(msg.id)
        reactions_data = await self._build_reactions_data(reactions)

        await publish_to_many(
            member_ids,
            {
                "type": "reaction_update",
                "chat_id": msg.chat_id,
                "message_id": message_id,
                "reactions": reactions_data,
            },
        )

    async def remove_reaction(self, message_id: int, user_id: int, emoji: str) -> None:
        msg = await self.messages.get_by_id(message_id)
        if not msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Message not found"
            )

        await self.reactions.remove(msg.id, user_id, emoji)
        await self.db.commit()

        members = await self.members.get_members(msg.chat_id)
        member_ids = [m.user_id for m in members]
        reactions = await self.reactions.get_by_message(msg.id)
        reactions_data = await self._build_reactions_data(reactions)

        await publish_to_many(
            member_ids,
            {
                "type": "reaction_update",
                "chat_id": msg.chat_id,
                "message_id": message_id,
                "reactions": reactions_data,
            },
        )

    async def _build_reactions_data(self, reactions) -> list[dict]:
        """Вспомогательный метод — строит список реакций с правильными URL."""
        import os

        custom_emoji_ids = [r.custom_emoji_id for r in reactions if r.custom_emoji_id]
        custom_emoji_map = {}
        if custom_emoji_ids:
            result = await self.db.execute(
                select(CustomEmoji).where(CustomEmoji.id.in_(custom_emoji_ids))
            )
            for ce in result.scalars().all():
                custom_emoji_map[ce.id] = (
                    f"/media/emojis/{os.path.basename(ce.file_location)}"
                )

        data = []
        for r in reactions:
            item = {"emoji": r.emoji, "user_id": r.user_id}
            if r.custom_emoji_id and r.custom_emoji_id in custom_emoji_map:
                item["custom_emoji_url"] = custom_emoji_map[r.custom_emoji_id]
            data.append(item)
        return data

    async def get_username_by_id(self, user_id: int) -> str | None:
        user = await self.db.get(User, user_id)
        return user.username if user else None

    async def get_members(self, chat_id: int, requester_id: int) -> dict:
        if not await self.members.is_member(chat_id, requester_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not a member"
            )
        members = await self.members.get_members(chat_id)
        user_ids = [m.user_id for m in members]
        users = await self.db.execute(
            select(User.id, User.username).where(User.id.in_(user_ids))
        )
        username_map = {u.id: u.username for u in users.all()}
        return {
            "members": [
                {
                    "id": m.user_id,
                    "username": username_map.get(m.user_id),
                    "role": m.role,
                }
                for m in members
            ]
        }

    async def get_user_chats(self, user_id: int) -> list[Chat]:
        return await self.chats.get_user_chats(user_id)

    async def get_user_chats_list(self, current_user_id: int):
        # 1. Получаем данные из Repo (убедись, что в Repo добавлен media_id)
        chats_data = await self.chats.get_user_chats_with_details(current_user_id)

        # 2. Поиск собеседников для DM (без изменений)
        direct_chat_ids = [
            row.Chat.id for row in chats_data if row.Chat.type == ChatType.direct
        ]

        members_map = {}
        if direct_chat_ids:
            stmt = (
                select(ChatMember.chat_id, User.id, User.username)
                .join(User, User.id == ChatMember.user_id)
                .where(ChatMember.chat_id.in_(direct_chat_ids))
                .where(ChatMember.user_id != current_user_id)
            )
            members_res = await self.db.execute(stmt)
            for m in members_res.all():
                members_map[m.chat_id] = m

        result = []
        for row in chats_data:
            chat = row.Chat

            if row.last_msg_content:
                try:
                    last_msg = decrypt_text(row.last_msg_content)
                except (ValueError, TypeError, UnicodeDecodeError):
                    last_msg = row.last_msg_content
            else:
                last_msg = ""

            chat_info = {
                "id": chat.id,
                "type": chat.type,
                "name": chat.name,
                "last_message": last_msg,
                "last_msg_media_id": row.last_msg_media_id,
                "updated_at": row.last_msg_at or chat.created_at,
                "is_online": False,
                "other_user_id": None,
            }

            if chat.type == ChatType.direct and chat.id in members_map:
                m = members_map[chat.id]
                chat_info["name"] = m.username
                chat_info["other_user_id"] = m.id

            result.append(chat_info)

        return result

