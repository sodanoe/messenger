from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.connection_manager import manager
from app.repositories.message_repo import MessageRepository
from app.repositories.reaction_repo import ReactionRepository

ALLOWED_EMOJIS = {"❤️", "😂", "😮", "😢", "😡", "👍"}


def _serialize(reactions) -> list[dict]:
    return [{"emoji": r.emoji, "user_id": r.user_id} for r in reactions]


class ReactionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.reactions = ReactionRepository(db)
        self.messages = MessageRepository(db)

    async def react(self, message_id: int, user_id: int, emoji: str) -> list[dict]:
        if emoji not in ALLOWED_EMOJIS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Недопустимый эмодзи. Доступны: {', '.join(sorted(ALLOWED_EMOJIS))}",
            )

        msg = await self.messages.get_by_id(message_id)
        if not msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сообщение не найдено")

        # Только участники переписки могут реагировать
        if user_id not in (msg.sender_id, msg.receiver_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа")

        _, updated = await self.reactions.toggle(message_id, user_id, emoji)
        await self.db.commit()

        serialized = _serialize(updated)

        # WS-пуш обоим участникам переписки
        ws_payload = {
            "type": "reaction_update",
            "message_id": message_id,
            "reactions": serialized,
        }
        await manager.send_to(msg.sender_id, ws_payload)
        if msg.receiver_id != msg.sender_id:
            await manager.send_to(msg.receiver_id, ws_payload)

        return serialized
