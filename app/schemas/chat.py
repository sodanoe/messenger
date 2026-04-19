from pydantic import BaseModel


class CreateDirectChatRequest(BaseModel):
    user_id: int


class CreateGroupChatRequest(BaseModel):
    name: str
    member_ids: list[int]


class SendMessageRequest(BaseModel):
    content: str
    media_id: int | None = None
    reply_to_id: int | None = None


class EditMessageRequest(BaseModel):
    new_content: str


class AddMemberRequest(BaseModel):
    user_id: int


class AddReactionRequest(BaseModel):
    emoji: str
