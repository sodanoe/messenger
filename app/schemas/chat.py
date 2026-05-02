from typing import Self
from pydantic import BaseModel, model_validator


class CreateDirectChatRequest(BaseModel):
    user_id: int


class CreateGroupChatRequest(BaseModel):
    name: str
    member_ids: list[int]


class SendMessageRequest(BaseModel):
    # Убираем min_length=1 отсюда, чтобы Pydantic не ругался сразу
    content: str | None = None
    media_id: int | None = None
    reply_to_id: int | None = None

    @model_validator(mode="after")
    def check_content_or_media(self) -> Self:
        # Проверяем: либо текст не пустой, либо есть картинка
        content_is_empty = not self.content or not self.content.strip()

        if content_is_empty and self.media_id is None:
            raise ValueError(
                "Сообщение не может быть пустым. Введите текст или прикрепите файл."
            )
        return self


class EditMessageRequest(BaseModel):
    new_content: str


class AddMemberRequest(BaseModel):
    user_id: int


class AddReactionRequest(BaseModel):
    emoji: str
