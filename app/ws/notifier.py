from app.ws.pubsub import publish_to_many


class ChatNotifier:
    """Типизированная обёртка над publish/publish_to_many.
    Сервисы не знают про формат WS-пейлоадов — знает только notifier."""

    async def new_message(
        self,
        member_ids: list[int],
        sender_id: int,
        payload: dict,
    ) -> None:
        # Параллельная рассылка через publish_to_many (asyncio.gather внутри)
        recipients = [uid for uid in member_ids if uid != sender_id]
        await publish_to_many(recipients, payload)

    async def message_deleted(
        self,
        member_ids: list[int],
        chat_id: int,
        message_id: int,
    ) -> None:
        await publish_to_many(
            member_ids,
            {
                "type": "message_deleted",
                "chat_id": chat_id,
                "message_id": message_id,
            },
        )

    async def message_edited(
        self,
        member_ids: list[int],
        message_id: int,
    ) -> None:
        await publish_to_many(
            member_ids,
            {
                "type": "message_edited",
                "message_id": message_id,
            },
        )

    async def reaction_update(
        self,
        member_ids: list[int],
        chat_id: int,
        message_id: int,
        reactions: list[dict],
    ) -> None:
        await publish_to_many(
            member_ids,
            {
                "type": "reaction_update",
                "chat_id": chat_id,
                "message_id": message_id,
                "reactions": reactions,
            },
        )

    async def member_added(
        self,
        user_id: int,
        chat_id: int,
        chat_name: str | None,
    ) -> None:
        await publish(
            user_id,
            {
                "type": "group_member_added",
                "chat_id": chat_id,
                "chat_name": chat_name,
            },
        )

    async def member_removed(
        self,
        user_id: int,
        chat_id: int,
        chat_name: str | None,
    ) -> None:
        await publish(
            user_id,
            {
                "type": "member_removed",
                "chat_id": chat_id,
                "chat_name": chat_name,
            },
        )

    async def chat_deleted(self, member_ids: list[int], chat_id: int) -> None:
        await publish_to_many(
            member_ids,
            {
                "type": "chat_deleted",
                "chat_id": chat_id,
            },
        )
