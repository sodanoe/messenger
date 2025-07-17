from .base import Base
from .user import User
from .chat import Chat, ChatMember
from .message import Message

# Для правильного разрешения relationship
__all__ = ["Base", "User", "Chat", "ChatMember", "Message"]
