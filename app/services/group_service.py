from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crypto.factory import get_crypto
from app.models.group import GroupRole
from app.repositories.group_repo import GroupRepository
from app.core.connection_manager import manager
from app.repositories.user_repo import UserRepository


class GroupService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.groups = GroupRepository(db)
        self.users = UserRepository(db)
        self.crypto = get_crypto()

    # ── helpers ──────────────────────────────────────────────

    async def _get_membership_or_403(self, group_id: int, user_id: int):
        """Returns GroupMember or raises 403."""
        group = await self.groups.get_by_id(group_id)
        if not group:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
        member = await self.groups.get_membership(group_id, user_id)
        if not member:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a group member")
        return group, member

    async def _require_admin(self, group_id: int, user_id: int):
        group, member = await self._get_membership_or_403(group_id, user_id)
        if member.role != GroupRole.admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
        return group, member

    # ── Groups ───────────────────────────────────────────────

    async def list_groups(self, me: int) -> list[dict]:
        groups = await self.groups.list_for_user(me)
        return [{"id": g.id, "name": g.name, "created_by": g.created_by, "created_at": g.created_at} for g in groups]

    async def create_group(self, me: int, name: str) -> dict:
        group = await self.groups.create(name, me)
        await self.groups.add_member(group.id, me, GroupRole.admin)
        await self.db.commit()
        return {"id": group.id, "name": group.name, "created_by": group.created_by, "created_at": group.created_at}

    async def delete_group(self, me: int, group_id: int) -> None:
        group, _ = await self._require_admin(group_id, me)
        await self.groups.delete(group)
        await self.db.commit()

    # ── Members ──────────────────────────────────────────────

    async def list_members(self, me: int, group_id: int) -> list[dict]:
        await self._get_membership_or_403(group_id, me)
        members = await self.groups.list_members(group_id)
        result = []
        for m in members:
            user = await self.users.get_by_id(m.user_id)
            result.append({
                "user_id": m.user_id,
                "username": user.username if user else None,
                "role": m.role,
            })
        return result

    async def invite_member(self, me: int, group_id: int, username: str) -> dict:
        await self._require_admin(group_id, me)

        target = await self.users.get_by_username(username)
        if not target:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        existing = await self.groups.get_membership(group_id, target.id)
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already in group")

        member = await self.groups.add_member(group_id, target.id, GroupRole.member)
        await self.db.commit()
        return {"user_id": target.id, "username": target.username, "role": member.role}

    async def remove_member(self, me: int, group_id: int, target_user_id: int) -> None:
        _, my_membership = await self._get_membership_or_403(group_id, me)

        if target_user_id == me:
            # Self-leave — any role allowed
            await self.groups.remove_member(group_id, me)
            await self.db.commit()
            return

        # Kicking someone else — must be admin
        if my_membership.role != GroupRole.admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")

        target = await self.groups.get_membership(group_id, target_user_id)
        if not target:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

        await self.groups.remove_member(group_id, target_user_id)
        await self.db.commit()

    # ── Messages ─────────────────────────────────────────────

    async def get_messages(self, me: int, group_id: int, cursor: int | None) -> dict:
        await self._get_membership_or_403(group_id, me)
        msgs = await self.groups.get_messages(group_id, cursor)
        next_cursor = msgs[-1].id if len(msgs) == 50 else None
        return {
            "messages": [
                {
                    "id": m.id,
                    "sender_id": m.sender_id,
                    "content": self.crypto.decrypt(m.content_encrypted),
                    "created_at": m.created_at,
                }
                for m in msgs
            ],
            "next_cursor": next_cursor,
        }

    async def send_message(self, me: int, group_id: int, content: str) -> dict:
        await self._get_membership_or_403(group_id, me)
        encrypted = self.crypto.encrypt(content)
        msg = await self.groups.create_message(group_id, me, encrypted)
        await self.db.commit()

        # WS fan-out — доставляем всем участникам группы кроме отправителя
        member_ids = await self.groups.get_member_ids(group_id)
        recipient_ids = [uid for uid in member_ids if uid != me]
        await manager.send_to_many(
            recipient_ids,
            {
                "type": "group_message",
                "group_id": group_id,
                "from": me,
                "content": content,
                "created_at": msg.created_at.isoformat(),
            },
        )

        return {
            "id": msg.id,
            "group_id": msg.group_id,
            "sender_id": msg.sender_id,
            "content": content,
            "created_at": msg.created_at,
        }
