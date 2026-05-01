import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.routers import (
    admin,
    auth,
    chat,
    contacts,
    emojis,
    media,
    members,
    messages,
    reactions,
    users,
    ws,
)

logger = logging.getLogger(__name__)


async def _media_cleanup_loop() -> None:
    """Удаляет медиафайлы старше MEDIA_TTL_DAYS раз в 24 часа."""
    await asyncio.sleep(10)
    while True:
        try:
            from app.core.database import AsyncSessionLocal
            from app.services.media_service import MediaService

            async with AsyncSessionLocal() as db:
                deleted = await MediaService(db).cleanup_old_files()
                if deleted:
                    logger.info("Media cleanup: removed %s files", deleted)
        except Exception:
            logger.exception("Media cleanup error")
        await asyncio.sleep(86400)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.ws.pubsub import start_listener

    pubsub_task = asyncio.create_task(start_listener())
    cleanup_task = asyncio.create_task(_media_cleanup_loop())

    yield

    cleanup_task.cancel()
    pubsub_task.cancel()
    try:
        await asyncio.gather(cleanup_task, pubsub_task, return_exceptions=True)
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Messenger API", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(contacts.router)
app.include_router(users.router)
app.include_router(ws.router)
app.include_router(media.router)
app.include_router(admin.router)
app.include_router(emojis.router)
# ── chat domain (все под /chats/...) ──────────
app.include_router(chat.router)
app.include_router(messages.router)
app.include_router(members.router)
app.include_router(reactions.router)

# ── Static media ──────────────────────────────
os.makedirs("/app/media/emojis", exist_ok=True)
os.makedirs("/app/media", exist_ok=True)
app.mount("/media", StaticFiles(directory="/app/media"), name="media")


@app.get("/sw.js", include_in_schema=False)
async def serve_sw():
    return FileResponse("app/static/sw.js")
