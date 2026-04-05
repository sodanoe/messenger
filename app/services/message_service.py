from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crypto.factory import get_crypto
from app.models.contact import ContactStatus
from app.repositories.contact_repo import ContactRepository
from app.repositories.message_repo import MessageRepository
from app.repositories.media_repo import MediaRepository
from app.repositories.reaction_repo import ReactionRepository
from app.core.connection_manager import manager


class MessageService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.messages = MessageRepository(db)
        self.contacts = ContactRepository(db)
        self.media = MediaRepository(db)
        self.reactions = ReactionRepository(db)
        self.crypto = get_crypto()

    async def get_history(self, me: int, other_id: int, cursor: int | None) -> dict:
        contact = await self.contacts.get(me, other_id)
        if not contact:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not in contacts"
            )

        msgs = await self.messages.get_history(me, other_id, cursor)
        next_cursor = msgs[-1].id if len(msgs) == 50 else None

        # Батч-запрос реакций — один запрос вместо N
        msg_ids = [m.id for m in msgs]
        all_reactions = await self.reactions.get_for_messages(msg_ids)
        reactions_by_msg: dict[int, list[dict]] = {}
        for r in all_reactions:
            reactions_by_msg.setdefault(r.message_id, []).append(
                {"emoji": r.emoji, "user_id": r.user_id}
            )

        # Батч-запрос цитируемых сообщений — один запрос вместо N
        reply_ids = [m.reply_to_id for m in msgs if m.reply_to_id]
        reply_map = {m.id: m for m in await self.messages.get_by_ids(reply_ids)}

        messages = []
        for m in msgs:
            msg_data: dict = {
                "id": m.id,
                "sender_id": m.sender_id,
                "content": self.crypto.decrypt(m.content_encrypted),
                "created_at": m.created_at,
                "reactions": reactions_by_msg.get(m.id, []),
                "reply_to": None,
                "read_at": m.read_at,
            }

            if m.reply_to_id and m.reply_to_id in reply_map:
                orig = reply_map[m.reply_to_id]

                reply_obj = {
                    "id": orig.id,
                    "sender_id": orig.sender_id,
                    "content": self.crypto.decrypt(orig.content_encrypted)[:120],
                }

                if orig.media_id:
                    media = await self.media.get_by_id(orig.media_id)
                    if media:
                        reply_obj["media_url"] = media.path

                msg_data["reply_to"] = reply_obj

            if m.media_id:
                media = await self.media.get_by_id(m.media_id)
                if media:
                    msg_data["media_url"] = media.path

            messages.append(msg_data)

        return {
            "messages": messages,
            "next_cursor": next_cursor,
        }

    async def send_message(
        self,
        me: int,
        receiver_id: int,
        content: str,
        media_id: int | None = None,
        reply_to_id: int | None = None,
    ) -> dict:
        contact = await self.contacts.get(me, receiver_id)
        if not contact:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not in contacts"
            )
        if contact.status == ContactStatus.blocked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Contact is blocked"
            )

        reverse = await self.contacts.get(receiver_id, me)
        if reverse and reverse.status == ContactStatus.blocked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are blocked by this user",
            )

        if media_id:
            media = await self.media.get_by_id(media_id)
            if not media or media.uploader_id != me:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="Invalid media file"
                )

        # Валидируем reply_to_id: сообщение должно принадлежать этой переписке
        reply_info: dict | None = None
        if reply_to_id:
            reply_msg = await self.messages.get_by_id(reply_to_id)
            participants = {me, receiver_id}
            if (
                reply_msg
                and reply_msg.sender_id in participants
                and reply_msg.receiver_id in participants
            ):
                reply_info = {
                    "id": reply_msg.id,
                    "sender_id": reply_msg.sender_id,
                    "content": self.crypto.decrypt(reply_msg.content_encrypted)[:120],
                }

                if reply_msg.media_id:
                    media = await self.media.get_by_id(reply_msg.media_id)
                    if media:
                        reply_info["media_url"] = media.path
            else:
                reply_to_id = None  # игнорируем невалидный reply

        encrypted = self.crypto.encrypt(content)
        msg = await self.messages.create(
            me, receiver_id, encrypted, media_id, reply_to_id
        )

        if media_id:
            await self.media.assign_to_message(media_id, msg.id)

        await self.contacts.set_unread(receiver_id, me, True)
        await self.db.commit()

        response: dict = {
            "id": msg.id,
            "sender_id": msg.sender_id,
            "receiver_id": msg.receiver_id,
            "content": content,
            "created_at": msg.created_at,
            "reply_to": reply_info,
            "reactions": [],
        }
        if media_id:
            response["media_url"] = media.path

        ws_payload: dict = {
            "type": "new_message",
            "id": msg.id,
            "from": me,
            "content": content,
            "created_at": msg.created_at.isoformat(),
            "reply_to": reply_info,
            "reactions": [],
        }
        if media_id:
            ws_payload["media_url"] = media.path

        await manager.send_to(receiver_id, ws_payload)

        return response

    async def mark_read(self, me: int, other_id: int) -> None:
        contact = await self.contacts.get(me, other_id)
        if not contact:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not in contacts"
            )
        await self.messages.mark_read_by_sender(other_id, me)
        await self.contacts.set_unread(me, other_id, False)
        await self.db.commit()

    async def delete_message(self, me: int, message_id: int) -> None:
        msg = await self.messages.get_by_id(message_id)
        if not msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Сообщение не найдено"
            )
        if msg.sender_id != me:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нельзя удалить чужое сообщение",
            )
        await self.messages.delete(msg)
        await self.db.commit()
        await manager.send_to(
            msg.receiver_id, {"type": "message_deleted", "message_id": message_id}
        )
        await manager.send_to(me, {"type": "message_deleted", "message_id": message_id})
