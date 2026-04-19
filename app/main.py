import os
from pathlib import Path
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from app.routers import (
    auth,
    contacts,
    users,
    ws,
    media,
    admin,
    chat,
    emojis,
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
        except Exception as exc:
            logger.error("Media cleanup error: %s", exc)
        await asyncio.sleep(86400)


@asynccontextmanager
async def lifespan(app: FastAPI):

    # 2. Pub/Sub listener для WebSocket multi-worker доставки
    from app.ws.pubsub import start_listener

    pubsub_task = asyncio.create_task(start_listener())

    # 3. Media cleanup loop
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
app.include_router(chat.router)
app.include_router(emojis.router)

# ── Static frontend ────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="app/static"), name="static")

os.makedirs("/app/media/emojis", exist_ok=True)
app.mount("/media/emojis", StaticFiles(directory="/app/media/emojis"), name="emojis")


@app.get("/sw.js", include_in_schema=False)
async def serve_sw():
    return FileResponse("app/static/sw.js")


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_index():
    return Path("app/static/index.html").read_text()
