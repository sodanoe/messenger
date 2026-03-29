from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.redis_client import get_redis
from app.models.user import User
from app.services.contact_service import ContactService

router = APIRouter(prefix="/contacts", tags=["contacts"])


class AddContactRequest(BaseModel):
    username: str


@router.get("")
async def list_contacts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    redis = get_redis()
    return await ContactService(db).list_contacts(current_user.id, redis)


@router.post("", status_code=201)
async def add_contact(
    body: AddContactRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await ContactService(db).add_contact(current_user.id, body.username)


@router.delete("/{contact_user_id}", status_code=204)
async def delete_contact(
    contact_user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await ContactService(db).delete_contact(current_user.id, contact_user_id)


@router.post("/{contact_user_id}/block", status_code=204)
async def block_contact(
    contact_user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await ContactService(db).block_contact(current_user.id, contact_user_id)
