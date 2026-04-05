from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_admin_user, get_current_user
from app.models.user import User
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6)
    invite_code: str


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    return await AuthService(db).register(
        body.username, body.password, body.invite_code
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    return await AuthService(db).login(body.username, body.password)


@router.post("/logout", status_code=204)
async def logout(_: User = Depends(get_current_user)):
    """Stateless — client discards the token."""


@router.post("/invite")
async def create_invite(
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    return await AuthService(db).generate_invite(admin.id)


@router.post("/ws/ticket")
async def get_ws_ticket(
    current_user: User = Depends(get_current_user),
):
    """Выдаёт одноразовый короткоживущий токен для WS-подключения."""
    from app.core.redis_client import get_redis
    import secrets

    redis = get_redis()
    ticket = secrets.token_hex(16)
    await redis.set(f"ws:ticket:{ticket}", str(current_user.id), ex=30)
    return {"ticket": ticket}
