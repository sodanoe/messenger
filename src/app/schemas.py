from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, List


# Базовые схемы для User
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=100)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Схемы для токенов
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None


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


# Схемы для создания приватного чата
class PrivateChatCreate(BaseModel):
    other_user_id: int


# Схемы для приглашения пользователя
class InviteUserRequest(BaseModel):
    user_id: int


# Схемы для ответов API
class MessageResponse(BaseModel):
    message: str


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


class UserStats(BaseModel):
    total_chats: int
    total_messages: int
    joined_at: datetime
