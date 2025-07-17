from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


# Схемы для создания приватного чата
class PrivateChatCreate(BaseModel):
    other_user_id: int


# Схемы для ответов API


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None


# Схемы для пагинации
class PaginationParams(BaseModel):
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class PaginatedResponse(BaseModel):
    items: List[dict]
    total: int
    limit: int
    offset: int
    has_next: bool
    has_prev: bool


# Схемы для поиска
class SearchParams(BaseModel):
    query: str = Field(..., min_length=1, max_length=100)
    chat_id: Optional[int] = None


# Схемы для статистики
class ChatStats(BaseModel):
    total_messages: int
    total_members: int
    last_message_at: Optional[datetime] = None
