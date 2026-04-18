from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crypto.service import encrypt_text
from app.models.contact import ContactStatus
from app.repositories.chat.chat_repo import ChatRepo
from app.repositories.chat.member_repo import MemberRepo
from app.repositories.chat.message_repo import MessageRepo
from app.repositories.chat.reaction_repo import ReactionRepo
from app.models.chat import ChatType, ChatRole, Chat
from app.repositories.contact_repo import ContactRepository
from app.repositories.media_repo import MediaRepository
from app.ws.pubsub import publish


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
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member")

        # 2. Для DM — дополнительно проверить контакты и блокировки
        chat = await self.chats.get_by_id(chat_id)
        if chat.type == ChatType.direct:
            other_id = await self._get_other_member_id(chat_id, sender_id)
            contact = await self.contacts.get(sender_id, other_id)
            if not contact:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not in contacts")
            if contact.status == ContactStatus.blocked:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Contact is blocked")
            reverse = await self.contacts.get(other_id, sender_id)
            if reverse and reverse.status == ContactStatus.blocked:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are blocked")

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
        ws_payload = {
            "type": "new_message",
            "id": msg.id,
            "chat_id": chat_id,
            "sender_id": sender_id,
            "content": content,
            "created_at": msg.created_at.isoformat(),
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
        }

    async def _get_other_member_id(self, chat_id: int, me: int) -> int:
        """Вспомогательный метод — найти второго участника DM чата."""
        members = await self.members.get_members(chat_id)
        for m in members:
            if m.user_id != me:
                return m.user_id
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat member not found")
