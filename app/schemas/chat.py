from datetime import datetime
from typing import Self

from pydantic import BaseModel, model_validator


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


class CreateDirectChatRequest(BaseModel):
    user_id: int


class CreateGroupChatRequest(BaseModel):
    name: str
    member_ids: list[int]


class SendMessageRequest(BaseModel):
    content: str | None = None
    media_id: int | None = None
    reply_to_id: int | None = None

    @model_validator(mode="after")
    def check_content_or_media(self) -> Self:
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


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------


class AvatarResponse(BaseModel):
    id: int
    url: str
    created_at: datetime


class UserResponse(BaseModel):
    id: int
    username: str
    last_seen: datetime


class UserSearchResponse(BaseModel):
    id: int
    username: str


class ContactResponse(BaseModel):
    id: int
    contact_user_id: int
    username: str | None
    status: str
    has_unread: bool
    is_online: bool
    last_message: str | None = None


class MediaResponse(BaseModel):
    id: int
    url: str
    original_name: str
    size: int


class ChatResponse(BaseModel):
    id: int
    type: str
    name: str | None
    last_message: str | None
    last_msg_media_id: int | None
    updated_at: datetime
    is_online: bool
    has_unread: bool
    other_user_id: int | None


class ChatListResponse(BaseModel):
    chats: list[ChatResponse]


class ReactionResponse(BaseModel):
    emoji: str
    user_id: int
    custom_emoji_url: str | None = None


class ReplyResponse(BaseModel):
    id: int
    sender_id: int
    sender_username: str | None = None
    content: str
    media_url: str | None = None


class MessageResponse(BaseModel):
    id: int
    chat_id: int
    sender_id: int
    sender_username: str | None = None
    content: str
    created_at: datetime
    reactions: list[ReactionResponse] = []
    reply_to: ReplyResponse | None = None
    reply_to_id: int | None = None
    media_url: str | None = None


class MessageHistoryResponse(BaseModel):
    messages: list[MessageResponse]
    next_cursor: int | None


class MemberResponse(BaseModel):
    id: int
    username: str | None
    role: str


class MemberListResponse(BaseModel):
    members: list[MemberResponse]


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class InviteResponse(BaseModel):
    code: str


class WsTicketResponse(BaseModel):
    ticket: str
