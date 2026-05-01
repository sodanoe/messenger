import os

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import CustomEmoji
from app.repositories.chat.member_repo import MemberRepo
from app.repositories.chat.message_repo import MessageRepo
from app.repositories.chat.reaction_repo import ReactionRepo
from app.ws.notifier import ChatNotifier


class ReactionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.messages = MessageRepo(db)
        self.members = MemberRepo(db)
        self.reactions = ReactionRepo(db)
        self.notifier = ChatNotifier()

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
        await self.notifier.reaction_update(
            member_ids, msg.chat_id, message_id, reactions_data
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
        await self.notifier.reaction_update(
            member_ids, msg.chat_id, message_id, reactions_data
        )

    async def _build_reactions_data(self, reactions) -> list[dict]:
        custom_emoji_ids = [r.custom_emoji_id for r in reactions if r.custom_emoji_id]
        custom_emoji_map: dict[int, str] = {}
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
