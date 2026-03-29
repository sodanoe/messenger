from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.core.config import settings

ALGORITHM = "HS256"


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)


def decode_access_token(token: str) -> int:
    """Returns user_id (int) or raises JWTError."""
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
    sub = payload.get("sub")
    if sub is None:
        raise JWTError("Missing sub claim")
    return int(sub)
