from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.group import Group, GroupMember, GroupMessage, GroupRole


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

    async def add_member(self, group_id: int, user_id: int, role: GroupRole = GroupRole.member) -> GroupMember:
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
        self, group_id: int, sender_id: int, content_encrypted: str
    ) -> GroupMessage:
        msg = GroupMessage(
            group_id=group_id,
            sender_id=sender_id,
            content_encrypted=content_encrypted,
        )
        self.db.add(msg)
        await self.db.flush()
        await self.db.refresh(msg)
        return msg
