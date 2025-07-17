from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

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


class UserStats(BaseModel):
    total_chats: int
    total_messages: int
    joined_at: datetime
