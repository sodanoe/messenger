from pathlib import Path
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.core.database import engine
from app.models import Base
from app.routers import (
    auth,
    contacts,
    groups,
    messages,
    users,
    ws,
    media,
    admin,
    reactions,
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
    task = asyncio.create_task(_media_cleanup_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Messenger API", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(contacts.router)
app.include_router(messages.router)
app.include_router(reactions.router)
app.include_router(users.router)
app.include_router(groups.router)
app.include_router(ws.router)
app.include_router(media.router)
app.include_router(admin.router)

# ── Static frontend ────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_index():
    return Path("app/static/index.html").read_text()
