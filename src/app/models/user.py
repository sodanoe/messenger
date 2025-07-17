from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)

    # Relationships (импорты будут в __init__.py)
    messages = relationship("Message", back_populates="author")
    chat_members = relationship("ChatMember", back_populates="user")
