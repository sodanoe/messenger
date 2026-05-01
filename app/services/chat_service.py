from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crypto.service import decrypt_text
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

    async def delete_chat(self, chat_id: int, user_id: int) -> None:
        chat = await self.chats.get_by_id(chat_id)
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Чат не найден"
            )
        members = await self.members.get_members(chat_id)
        requester = next((m for m in members if m.user_id == user_id), None)
        if not requester:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not a member"
            )
        if chat.type == ChatType.group and requester.role != ChatRole.admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can delete group",
            )
        member_ids = [m.user_id for m in members]
        await self.db.delete(chat)
        await self.db.commit()
        await self.notifier.chat_deleted(member_ids, chat_id)
