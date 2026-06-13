import asyncio
from fastapi import HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.crypto.service import async_decrypt_safe
from app.models.chat import Chat, ChatMember, ChatRole, ChatType
from app.models.contact import Contact
from app.models.user import User
from app.repositories.chat.chat_repo import ChatRepo
from app.repositories.chat.member_repo import MemberRepo
from app.repositories.contact_repo import ContactRepository
from app.ws.notifier import ChatNotifier


class ChatService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.chats = ChatRepo(db)
        self.members = MemberRepo(db)
        self.contacts = ContactRepository(db)
        self.notifier = ChatNotifier()

    async def create_direct_chat(self, user_a_id: int, user_b_id: int) -> Chat:
        if user_a_id == user_b_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Нельзя создать чат с самим собой",
            )

        other_user = await self.db.get(User, user_b_id)
        if not other_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден",
            )

        member_b = ChatMember.__table__.alias("member_b")
        stmt = (
            select(Chat)
            .join(
                ChatMember,
                and_(ChatMember.chat_id == Chat.id, ChatMember.user_id == user_a_id),
            )
            .join(
                member_b,
                and_(member_b.c.chat_id == Chat.id, member_b.c.user_id == user_b_id),
            )
            .where(Chat.type == ChatType.direct)
            .limit(1)
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            return existing

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

    async def get_user_chats(self, user_id: int) -> list[Chat]:
        return await self.chats.get_user_chats(user_id)

    async def get_user_chats_list(self, current_user_id: int):
        chats_data = await self.chats.get_user_chats_with_details(current_user_id)

        direct_chat_ids = [
            row.Chat.id for row in chats_data if row.Chat.type == ChatType.direct
        ]

        members_map: dict = {}
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

        other_user_ids = [m.id for m in members_map.values()]
        unread_map: dict[int, bool] = {}
        if other_user_ids:
            contacts_res = await self.db.execute(
                select(Contact.contact_user_id, Contact.has_unread).where(
                    Contact.user_id == current_user_id,
                    Contact.contact_user_id.in_(other_user_ids),
                )
            )
            for row in contacts_res.all():
                unread_map[row.contact_user_id] = row.has_unread

        decrypted = await asyncio.gather(
            *[async_decrypt_safe(row.last_msg_content) for row in chats_data]
        )

        result = []
        for row, last_msg in zip(chats_data, decrypted):
            chat = row.Chat

            chat_info = {
                "id": chat.id,
                "type": chat.type,
                "name": chat.name,
                "last_message": last_msg,
                "last_msg_media_id": row.last_msg_media_id,
                "updated_at": row.last_msg_at or chat.created_at,
                "is_online": False,
                "has_unread": False,
                "other_user_id": None,
            }

            if chat.type == ChatType.direct and chat.id in members_map:
                m = members_map[chat.id]
                chat_info["name"] = m.username
                chat_info["other_user_id"] = m.id
                chat_info["has_unread"] = unread_map.get(m.id, False)

            result.append(chat_info)

        return result

    async def require_admin(self, chat_id: int, user_id: int) -> None:
        """Бросает 403 если юзер не участник или не админ."""
        member = await self.members.get_single_member(chat_id, user_id)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not a member"
            )
        if member.role != ChatRole.admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Admins only"
            )

    async def require_group(self, chat_id: int) -> Chat:
        """Бросает 404 если чат не найден, 400 если это не группа."""
        chat = await self.chats.get_by_id(chat_id)
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Чат не найден"
            )
        if chat.type != ChatType.group:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Аватарка доступна только для групп",
            )
        return chat

    async def delete_chat(self, chat_id: int, user_id: int) -> None:
        chat = await self.chats.get_by_id(chat_id)
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Чат не найден"
            )
        # Переиспользуем require_admin вместо дублирования проверки
        if chat.type == ChatType.group:
            await self.require_admin(chat_id, user_id)
        else:
            member = await self.members.get_single_member(chat_id, user_id)
            if not member:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="Not a member"
                )

        member_ids = await self.members.get_member_ids(chat_id)
        await self.db.delete(chat)
        await self.db.commit()
        await self.notifier.chat_deleted(member_ids, chat_id)
