from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

from src.app.schemas import UserResponse


# Схемы для сообщений
class MessageBase(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)


class MessageCreate(MessageBase):
    chat_id: int


class MessageEdit(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)


class MessageResponse(MessageBase):
    id: int
    chat_id: int
    author_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_edited: bool

    class Config:
        from_attributes = True


class MessageWithAuthor(MessageResponse):
    author: UserResponse

    class Config:
        from_attributes = True
