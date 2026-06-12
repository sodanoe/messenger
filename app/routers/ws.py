import logging

from fastapi import APIRouter, Query, WebSocket

from app.core.redis_client import get_redis
from app.ws.session import WsSession

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/ws")
async def websocket_endpoint(
    ws: WebSocket,
    ticket: str = Query(..., description="One-time WS ticket from /auth/ws/ticket"),
) -> None:
    # ── Auth ─────────────────────────────────────────────────────────
    redis = get_redis()
    user_id_str = await redis.getdel(f"ws:ticket:{ticket}")
    if not user_id_str:
        await ws.close(code=1008)
        return

    session = WsSession(int(user_id_str), ws, redis)

    # ── Connect ──────────────────────────────────────────────────────
    await session.connect()

    # ── Receive loop ─────────────────────────────────────────────────
    try:
        await session.run()
    except Exception as exc:
        logger.warning("WS error user_id=%s: %s", session.user_id, exc)

    # ── Cleanup ──────────────────────────────────────────────────────
    finally:
        await session.cleanup()
