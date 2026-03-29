import enum

from sqlalchemy import Boolean, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ContactStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    blocked = "blocked"


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    contact_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    has_unread: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[ContactStatus] = mapped_column(
        Enum(ContactStatus, name="contact_status"), default=ContactStatus.pending, nullable=False
    )
