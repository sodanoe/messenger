from sqlalchemy import Column, Integer, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class Message(Base, TimestampMixin):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=False)
    chat_id = Column(Integer, ForeignKey("chats.id", ondelete="CASCADE"))
    author_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    is_edited = Column(Boolean, default=False, nullable=False)

    # Relationships
    chat = relationship("Chat", back_populates="messages")
    author = relationship("User", back_populates="messages")
