from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)

    messages = relationship("Message", back_populates="author")


class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)

    messages = relationship("Message", back_populates="chat")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(String)
    chat_id = Column(Integer, ForeignKey("chats.id"))
    author_id = Column(Integer, ForeignKey("users.id"))

    chat = relationship("Chat", back_populates="messages")
    author = relationship("User", back_populates="messages")
