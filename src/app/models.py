from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    messages = relationship("Message", back_populates="author")
    chat_members = relationship("ChatMember", back_populates="user")


class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True, nullable=False)
    description = Column(Text, nullable=True)
    is_group = Column(
        Boolean, default=True, nullable=False
    )  # True для группы, False для личного чата
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    messages = relationship("Message", back_populates="chat")
    chat_members = relationship("ChatMember", back_populates="chat")


class ChatMember(Base):
    """Промежуточная таблица для связи многие-ко-многим между User и Chat"""

    __tablename__ = "chat_members"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    chat_id = Column(Integer, ForeignKey("chats.id", ondelete="CASCADE"))
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    role = Column(String(20), default="member")  # member, admin, owner

    # Relationships
    user = relationship("User", back_populates="chat_members")
    chat = relationship("Chat", back_populates="chat_members")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=False)
    chat_id = Column(Integer, ForeignKey("chats.id", ondelete="CASCADE"))
    author_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_edited = Column(Boolean, default=False, nullable=False)

    # Relationships
    chat = relationship("Chat", back_populates="messages")
    author = relationship("User", back_populates="messages")
