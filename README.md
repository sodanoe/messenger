# messenger-backend

Self-hosted ICQ-style messenger. FastAPI + PostgreSQL + Redis + WebSockets.

## Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy (async), Alembic
- **DB**: PostgreSQL 16
- **Cache/Pub-Sub**: Redis 7
- **Frontend**: Vanilla JS (single-page, built-in)
- **Deploy**: Docker Compose + nginx + certbot

---

## Локальный запуск

```bash
bash setup_local.sh
```

Скрипт сам создаст `.env`, сгенерирует секреты, поднимет БД и Redis в Docker,
накатит миграции и запустит uvicorn. Открыть: http://localhost:8000

---

## Deploy на VPS

### 1. Что поправить перед деплоем

**`deploy/deploy.sh`** — настройки подключения к серверу:
```bash
REMOTE_USER="your_vps_user"       # ← пользователь на VPS
REMOTE_HOST="your.vps.ip"         # ← IP адрес VPS
REMOTE_DIR="/home/your_vps_user/messenger"  # ← путь на сервере
SSH_KEY="$HOME/.ssh/your_key"     # ← путь к SSH ключу
DOMAIN="your-domain.example.com"  # ← твой домен
```

**`deploy/nginx_vps.conf`** — три места с доменом и путём к медиа:
```nginx
server_name your-domain.example.com;
ssl_certificate /etc/letsencrypt/live/your-domain.example.com/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/your-domain.example.com/privkey.pem;
alias /home/your_vps_user/messenger/media/;
```

**`.env`** на сервере — создать из примера и заполнить:
```bash
cp .env.example .env
# Минимум поменять:
# POSTGRES_PASSWORD, JWT_SECRET, CRYPTO_KEY
```

> JWT_SECRET и CRYPTO_KEY можно сгенерировать командой: `openssl rand -hex 32`

### 2. Запустить деплой

```bash
bash deploy/deploy.sh
```

Скрипт соберёт Docker-образ, загрузит на сервер, запустит контейнеры,
накатит миграции, настроит nginx и выпустит SSL-сертификат через certbot.

---

## Миграции

```bash
# Создать новую миграцию
alembic revision --autogenerate -m "описание"

# Применить
alembic upgrade head
```

---

## Структура проекта

```
app/
├── core/          # конфиг, БД, JWT, Redis
├── models/        # SQLAlchemy модели
├── repositories/  # работа с БД
├── services/      # бизнес-логика
├── routers/       # FastAPI эндпоинты
├── crypto/        # шифрование сообщений
└── static/        # фронтенд (vanilla JS)
alembic/           # миграции БД
deploy/            # скрипты деплоя и nginx конфиг
```
