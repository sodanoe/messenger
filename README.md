# messenger-backend

Self-hosted ICQ-style messenger. FastAPI + PostgreSQL + Redis + WebSockets.

## Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy (async), Alembic
- **DB**: PostgreSQL 16
- **Cache/Pub-Sub**: Redis 7
- **Frontend**: Vanilla JS (single-page, built-in)
- **Deploy**: Docker Compose + nginx + certbot

## Быстрый старт (локально)
```bash
cp .env.example .env
# отредактируй .env — минимум DATABASE_URL, JWT_SECRET, CRYPTO_KEY

docker compose up -d          # поднять postgres + redis
alembic upgrade head           # накатить миграции
uvicorn app.main:app --reload  # запустить
```

Открыть: http://localhost:8000

## Deploy на VPS

1. Заполни переменные в `deploy/deploy.sh` (REMOTE_USER, REMOTE_HOST и т.д.)
2. Скопируй `.env.example` → `.env` на сервере, заполни секреты
3. Запусти: `bash deploy/deploy.sh`

Скрипт сам соберёт Docker-образ, загрузит на сервер, накатит миграции, настроит nginx + certbot.

## Миграции
```bash
# Создать новую миграцию
alembic revision --autogenerate -m "описание"

# Применить
alembic upgrade head
```
