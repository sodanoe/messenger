from typing import Annotated
from pydantic import BaseModel, Field, StringConstraints


class CreateDirectChatRequest(BaseModel):
    user_id: int


class CreateGroupChatRequest(BaseModel):
    name: str
    member_ids: list[int]


class SendMessageRequest(BaseModel):
    content: Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)]
    media_id: int | None = None
    reply_to_id: int | None = None


class EditMessageRequest(BaseModel):
    new_content: str


class AddMemberRequest(BaseModel):
    user_id: int


class AddReactionRequest(BaseModel):
    emoji: str