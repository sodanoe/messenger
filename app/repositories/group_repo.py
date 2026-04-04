from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.group import (
    Group,
    GroupMember,
    GroupMessage,
    GroupMessageReaction,
    GroupRole,
)


class GroupRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Groups ───────────────────────────────────────────────

    async def get_by_id(self, group_id: int) -> Group | None:
        result = await self.db.execute(select(Group).where(Group.id == group_id))
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: int) -> list[Group]:
        subq = select(GroupMember.group_id).where(GroupMember.user_id == user_id)
        result = await self.db.execute(select(Group).where(Group.id.in_(subq)))
        return list(result.scalars().all())

    async def create(self, name: str, created_by: int) -> Group:
        group = Group(name=name, created_by=created_by)
        self.db.add(group)
        await self.db.flush()
        await self.db.refresh(group)
        return group

    async def delete(self, group: Group) -> None:
        await self.db.delete(group)

    # ── Members ──────────────────────────────────────────────

    async def get_membership(self, group_id: int, user_id: int) -> GroupMember | None:
        result = await self.db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_members(self, group_id: int) -> list[GroupMember]:
        result = await self.db.execute(
            select(GroupMember).where(GroupMember.group_id == group_id)
        )
        return list(result.scalars().all())

    async def get_member_ids(self, group_id: int) -> list[int]:
        result = await self.db.execute(
            select(GroupMember.user_id).where(GroupMember.group_id == group_id)
        )
        return list(result.scalars().all())

    async def add_member(
        self, group_id: int, user_id: int, role: GroupRole = GroupRole.member
    ) -> GroupMember:
        member = GroupMember(group_id=group_id, user_id=user_id, role=role)
        self.db.add(member)
        await self.db.flush()
        await self.db.refresh(member)
        return member

    async def remove_member(self, group_id: int, user_id: int) -> None:
        await self.db.execute(
            delete(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == user_id,
            )
        )

    # ── Messages ─────────────────────────────────────────────

    async def get_message_by_id(self, message_id: int) -> GroupMessage | None:
        result = await self.db.execute(
            select(GroupMessage).where(GroupMessage.id == message_id)
        )
        return result.scalar_one_or_none()

    async def get_messages_by_ids(self, ids: list[int]) -> list[GroupMessage]:
        if not ids:
            return []
        result = await self.db.execute(
            select(GroupMessage).where(GroupMessage.id.in_(ids))
        )
        return list(result.scalars().all())

    async def get_messages(
        self,
        group_id: int,
        cursor: int | None,
        limit: int = 50,
    ) -> list[GroupMessage]:
        q = select(GroupMessage).where(GroupMessage.group_id == group_id)
        if cursor is not None:
            q = q.where(GroupMessage.id < cursor)
        q = q.order_by(GroupMessage.id.desc()).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def create_message(
        self,
        group_id: int,
        sender_id: int,
        content_encrypted: str,
        media_id: int | None = None,
        reply_to_id: int | None = None,
    ) -> GroupMessage:
        msg = GroupMessage(
            group_id=group_id,
            sender_id=sender_id,
            content_encrypted=content_encrypted,
            media_id=media_id,
            reply_to_id=reply_to_id,
        )
        self.db.add(msg)
        await self.db.flush()
        await self.db.refresh(msg)
        return msg

    async def delete_message(self, msg: GroupMessage) -> None:
        await self.db.delete(msg)

    # ── Reactions ─────────────────────────────────────────────

    async def get_reactions_for_messages(
        self, message_ids: list[int]
    ) -> list[GroupMessageReaction]:
        if not message_ids:
            return []
        result = await self.db.execute(
            select(GroupMessageReaction).where(
                GroupMessageReaction.message_id.in_(message_ids)
            )
        )
        return list(result.scalars().all())

    async def get_reactions_for_message(
        self, message_id: int
    ) -> list[GroupMessageReaction]:
        result = await self.db.execute(
            select(GroupMessageReaction).where(
                GroupMessageReaction.message_id == message_id
            )
        )
        return list(result.scalars().all())

    async def toggle_reaction(
        self,
        message_id: int,
        user_id: int,
        emoji: str,
    ) -> tuple[bool, list[GroupMessageReaction]]:
        existing = await self.db.execute(
            select(GroupMessageReaction).where(
                GroupMessageReaction.message_id == message_id,
                GroupMessageReaction.user_id == user_id,
                GroupMessageReaction.emoji == emoji,
            )
        )
        reaction = existing.scalar_one_or_none()

        if reaction:
            await self.db.delete(reaction)
            added = False
        else:
            self.db.add(
                GroupMessageReaction(
                    message_id=message_id,
                    user_id=user_id,
                    emoji=emoji,
                )
            )
            added = True

        await self.db.flush()
        updated = await self.get_reactions_for_message(message_id)
        return added, updated
