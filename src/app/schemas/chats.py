from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

from src.app.schemas.users import UserResponse
from src.app.schemas.messages import MessageResponse


# Схемы для чатов
class ChatBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    is_group: bool = True


class ChatCreate(ChatBase):
    pass


class ChatResponse(ChatBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ChatWithMembers(ChatResponse):
    members: List[UserResponse]

    class Config:
        from_attributes = True


class ChatWithMessages(ChatResponse):
    messages: List[MessageResponse]

    class Config:
        from_attributes = True
