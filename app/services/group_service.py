from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.connection_manager import manager
from app.crypto.factory import get_crypto
from app.repositories.group_repo import GroupRepository
from app.repositories.media_repo import MediaRepository
from app.repositories.user_repo import UserRepository
from app.models.group import GroupRole

ALLOWED_EMOJIS = {"❤️", "😂", "😮", "😢", "😡", "👍"}


class GroupService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = GroupRepository(db)
        self.media = MediaRepository(db)
        self.users = UserRepository(db)
        self.crypto = get_crypto()

    # ── Groups ───────────────────────────────────────────────

    async def list_groups(self, user_id: int) -> list[dict]:
        groups = await self.repo.list_for_user(user_id)
        return [
            {"id": g.id, "name": g.name, "created_by": g.created_by} for g in groups
        ]

    async def create_group(self, user_id: int, name: str) -> dict:
        group = await self.repo.create(name=name, created_by=user_id)
        await self.repo.add_member(group.id, user_id, role=GroupRole.admin)
        await self.db.commit()
        return {"id": group.id, "name": group.name}

    async def delete_group(self, user_id: int, group_id: int) -> None:
        group = await self._get_group_or_404(group_id)
        await self._require_admin(group_id, user_id)
        await self.repo.delete(group)
        await self.db.commit()

    # ── Members ──────────────────────────────────────────────

    async def list_members(self, user_id: int, group_id: int) -> list[dict]:
        await self._require_member(group_id, user_id)
        members = await self.repo.list_members(group_id)
        user_ids = [m.user_id for m in members]
        users = {u.id: u for u in await self.users.get_by_ids(user_ids)}
        return [
            {
                "user_id": m.user_id,
                "role": m.role,
                # .get() вместо [] — защита от удалённого юзера без CASCADE
                "username": users.get(m.user_id)
                and users[m.user_id].username
                or f"#{m.user_id}",
            }
            for m in members
            if m.user_id in users  # пропускаем записи-призраки
        ]

    async def invite_member(self, user_id: int, group_id: int, username: str) -> dict:
        await self._require_admin(group_id, user_id)
        target = await self.users.get_by_username(username)
        if not target:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден"
            )
        existing = await self.repo.get_membership(group_id, target.id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Уже в группе"
            )
        member = await self.repo.add_member(group_id, target.id)
        await self.db.commit()
        return {"user_id": member.user_id, "role": member.role}

    async def remove_member(self, user_id: int, group_id: int, target_id: int) -> None:
        await self._require_admin(group_id, user_id)
        await self._require_member(group_id, target_id)
        await self.repo.remove_member(group_id, target_id)
        await self.db.commit()

    async def leave_group(self, user_id: int, group_id: int) -> None:
        await self._require_member(group_id, user_id)
        await self.repo.remove_member(group_id, user_id)
        await self.db.commit()

    # ── Messages ─────────────────────────────────────────────

    async def get_messages(
        self, user_id: int, group_id: int, cursor: int | None
    ) -> dict:
        await self._require_member(group_id, user_id)
        msgs = await self.repo.get_messages(group_id, cursor)
        next_cursor = msgs[-1].id if len(msgs) == 50 else None

        # Батч реакций
        msg_ids = [m.id for m in msgs]
        all_reactions = await self.repo.get_reactions_for_messages(msg_ids)
        reactions_by_msg: dict[int, list[dict]] = {}
        for r in all_reactions:
            reactions_by_msg.setdefault(r.message_id, []).append(
                {"emoji": r.emoji, "user_id": r.user_id}
            )

        # Батч реплаев
        reply_ids = [m.reply_to_id for m in msgs if m.reply_to_id]
        reply_map = {m.id: m for m in await self.repo.get_messages_by_ids(reply_ids)}
        sender_ids = list({m.sender_id for m in msgs})
        sender_map = {u.id: u.username for u in await self.users.get_by_ids(sender_ids)}

        messages = []
        for m in msgs:
            msg_data: dict = {
                "id": m.id,
                "sender_id": m.sender_id,
                "content": self.crypto.decrypt(str(m.content_encrypted)),
                "created_at": m.created_at,
                "reactions": reactions_by_msg.get(m.id, []),
                "reply_to": None,
                "sender_username": sender_map.get(m.sender_id, f"#{m.sender_id}"),
            }

            if m.reply_to_id and m.reply_to_id in reply_map:
                orig = reply_map[m.reply_to_id]
                reply_obj = {
                    "id": orig.id,
                    "sender_id": orig.sender_id,
                    "content": self.crypto.decrypt(str(orig.content_encrypted))[:120],
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

        return {"messages": messages, "next_cursor": next_cursor}

    async def send_message(
        self,
        user_id: int,
        group_id: int,
        content: str,
        media_id: int | None = None,
        reply_to_id: int | None = None,
    ) -> dict:
        await self._require_member(group_id, user_id)

        msg_media = None
        if media_id:
            msg_media = await self.media.get_by_id(media_id)
            if not msg_media or msg_media.uploader_id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="Invalid media file"
                )

        reply_info: dict | None = None
        if reply_to_id:
            reply_msg = await self.repo.get_message_by_id(reply_to_id)
            if reply_msg and reply_msg.group_id == group_id:
                reply_info = {
                    "id": reply_msg.id,
                    "sender_id": reply_msg.sender_id,
                    "content": self.crypto.decrypt(str(reply_msg.content_encrypted))[
                        :120
                    ],
                }
                if reply_msg.media_id:
                    reply_media = await self.media.get_by_id(reply_msg.media_id)
                    if reply_media:
                        reply_info["media_url"] = reply_media.path
            else:
                reply_to_id = None

        encrypted = self.crypto.encrypt(content)
        msg = await self.repo.create_message(
            group_id, user_id, encrypted, media_id, reply_to_id
        )

        if media_id:
            await self.media.assign_to_message(media_id, msg.id)

        await self.db.commit()

        sender = await self.users.get_by_id(user_id)
        sender_username = sender.username if sender else f"#{user_id}"

        response: dict = {
            "id": msg.id,
            "sender_username": sender_username,
            "group_id": group_id,
            "sender_id": user_id,
            "content": content,
            "created_at": msg.created_at,
            "reply_to": reply_info,
            "reactions": [],
        }
        if media_id and msg_media:
            response["media_url"] = msg_media.path

        member_ids = await self.repo.get_member_ids(group_id)
        ws_payload: dict = {
            "type": "new_group_message",
            "group_id": group_id,
            "id": msg.id,
            "sender_username": sender_username,
            "from": user_id,
            "content": content,
            "created_at": msg.created_at.isoformat(),
            "reply_to": reply_info,
            "reactions": [],
        }
        if media_id and msg_media:
            ws_payload["media_url"] = msg_media.path

        await manager.send_to_many(member_ids, ws_payload)

        return response

    async def delete_message(
        self, user_id: int, group_id: int, message_id: int
    ) -> None:
        msg = await self.repo.get_message_by_id(message_id)
        if not msg or msg.group_id != group_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Сообщение не найдено"
            )
        if msg.sender_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нельзя удалить чужое сообщение",
            )
        await self.repo.delete_message(msg)
        await self.db.commit()
        member_ids = await self.repo.get_member_ids(group_id)
        await manager.send_to_many(
            member_ids,
            {
                "type": "group_message_deleted",
                "group_id": group_id,
                "message_id": message_id,
            },
        )

    # ── Reactions ─────────────────────────────────────────────

    async def react(
        self, user_id: int, group_id: int, message_id: int, emoji: str
    ) -> list[dict]:
        if emoji not in ALLOWED_EMOJIS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Недопустимый эмодзи. Доступны: {', '.join(sorted(ALLOWED_EMOJIS))}",
            )
        await self._require_member(group_id, user_id)
        msg = await self.repo.get_message_by_id(message_id)
        if not msg or msg.group_id != group_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Сообщение не найдено"
            )

        _, updated = await self.repo.toggle_reaction(message_id, user_id, emoji)
        await self.db.commit()

        serialized = [{"emoji": r.emoji, "user_id": r.user_id} for r in updated]

        member_ids = await self.repo.get_member_ids(group_id)
        ws_payload = {
            "type": "group_reaction_update",
            "group_id": group_id,
            "message_id": message_id,
            "reactions": serialized,
        }
        await manager.send_to_many(member_ids, ws_payload)

        return serialized

    # ── Helpers ───────────────────────────────────────────────

    async def _get_group_or_404(self, group_id: int):
        group = await self.repo.get_by_id(group_id)
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Группа не найдена"
            )
        return group

    async def _require_member(self, group_id: int, user_id: int):
        membership = await self.repo.get_membership(group_id, user_id)
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к группе"
            )

    async def _require_admin(self, group_id: int, user_id: int):
        membership = await self.repo.get_membership(group_id, user_id)
        if not membership or membership.role != GroupRole.admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Требуются права администратора",
            )
