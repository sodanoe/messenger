from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.core.config import settings

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 30


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": str(user_id), "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)


def decode_access_token(token: str) -> int:
    """Returns user_id (int) or raises JWTError."""
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])

    # Обратная совместимость: старые токены без поля type тоже принимаем
    # Отклоняем только если явно указан чужой тип
    if payload.get("type") == "refresh":
        raise JWTError("Wrong token type")

    sub = payload.get("sub")
    if sub is None:
        raise JWTError("Missing sub claim")
    return int(sub)


def decode_refresh_token(token: str) -> int:
    """Returns user_id (int) or raises JWTError."""
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
    if payload.get("type") != "refresh":
        raise JWTError("Wrong token type")
    sub = payload.get("sub")
    if sub is None:
        raise JWTError("Missing sub claim")
    return int(sub)
