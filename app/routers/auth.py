import secrets

from fastapi import APIRouter, Depends, Response, Cookie, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_admin_user, get_current_user
from app.core.redis_client import get_redis
from app.models.user import User
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "refresh_token"
COOKIE_OPTS = dict(
    key=REFRESH_COOKIE,
    httponly=True,
    secure=True,  # только HTTPS
    samesite="strict",
    max_age=30 * 86400,
    path="/auth",  # cookie летит только на /auth/*
)


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


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(value=token, **COOKIE_OPTS)


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE, path="/auth")


@router.post("/register", response_model=TokenResponse)
async def register(
    body: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    redis = get_redis()
    access, refresh = await AuthService(db).register(
        body.username, body.password, body.invite_code, redis
    )
    _set_refresh_cookie(response, refresh)
    return {"access_token": access, "token_type": "bearer"}


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    redis = get_redis()
    access, refresh = await AuthService(db).login(body.username, body.password, redis)
    _set_refresh_cookie(response, refresh)
    return {"access_token": access, "token_type": "bearer"}


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    response: Response,
    refresh: str | None = Cookie(default=None, alias=REFRESH_COOKIE),
):
    if not refresh:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token"
        )
    redis = get_redis()
    # db не нужна — только Redis + JWT
    access = await AuthService(db=None).refresh(refresh, redis)  # type: ignore[arg-type]
    return {"access_token": access, "token_type": "bearer"}


@router.post("/logout", status_code=204)
async def logout(
    response: Response,
    refresh: str | None = Cookie(default=None, alias=REFRESH_COOKIE),
):
    if refresh:
        redis = get_redis()
        await AuthService(db=None).logout(refresh, redis)  # type: ignore[arg-type]
    _clear_refresh_cookie(response)


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
    redis = get_redis()
    ticket = secrets.token_hex(16)
    await redis.set(f"ws:ticket:{ticket}", str(current_user.id), ex=30)
    return {"ticket": ticket}
