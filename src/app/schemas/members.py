from pydantic import BaseModel, Field
from datetime import datetime

from src.app.schemas import UserResponse


# Схемы для приглашения пользователя
class InviteUserRequest(BaseModel):
    user_id: int


# Схемы для участников чата
class ChatMemberBase(BaseModel):
    role: str = Field(default="member", pattern="^(member|admin|owner)$")


class ChatMemberResponse(ChatMemberBase):
    id: int
    user_id: int
    chat_id: int
    joined_at: datetime
    user: UserResponse

    class Config:
        from_attributes = True
