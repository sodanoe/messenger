import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

# Загружаем .env файл
from dotenv import load_dotenv

load_dotenv()  # ищет .env в текущей директории

from app.models import Base  # noqa: E402

config = context.config
fileConfig(config.config_file_name)  # type: ignore

target_metadata = Base.metadata


def run_migrations_offline():
    url = os.environ.get("DATABASE_URL")  # теперь переменная загружена
    if not url:
        raise ValueError("DATABASE_URL not found in environment")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL not found in environment")
    connectable = create_async_engine(url)
    async with connectable.connect() as connection:
        await connection.run_sync(
            lambda sync_conn: context.configure(
                connection=sync_conn, target_metadata=target_metadata
            )
        )
        async with connection.begin():
            await connection.run_sync(lambda _: context.run_migrations())
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
