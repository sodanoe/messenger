# messenger

Самохостящийся мессенджер. Монорепо: FastAPI бэкенд + React фронтенд.

---

## Стек

### Бэкенд
| | |
|---|---|
| Runtime | Python 3.12 |
| Фреймворк | FastAPI |
| ORM | SQLAlchemy (async) + Alembic |
| БД | PostgreSQL 16 |
| Кэш / Pub-Sub | Redis 7 |
| Авторизация | JWT (access + refresh токены) |
| Шифрование | AES-256-GCM (серверное) |
| Realtime | WebSockets + Redis Pub/Sub |
| Образ | Python 3.12 Alpine, multi-stage build |

### Фронтенд
| | |
|---|---|
| Фреймворк | React 19 + Vite |
| Состояние | Zustand |
| Роутинг | React Router v7 |
| Emoji | emoji-mart |
| 3D | Three.js + React Three Fiber |
| Уведомления | react-hot-toast |
| PWA | Web App Manifest + Service Worker |

---

## Функциональность

**Чаты**
- Личные и групповые чаты
- Ответы на сообщения (reply)
- Emoji-реакции на сообщения
- Доставка в реальном времени через WebSocket + Redis Pub/Sub (multi-worker)

**Медиа**
- Загрузка изображений (сжатие на сервере через Pillow, лимит 20 МБ)
- Автоматическая очистка файлов старше `MEDIA_TTL_DAYS` дней

**Пользователи**
- Регистрация по инвайт-кодам (инвайты создаёт администратор)
- Контакты с блокировкой
- Поиск пользователей

**Безопасность**
- Шифрование сообщений AES-256-GCM
- Rate limiting на авторизацию
- WebSocket-подключение через одноразовые тикеты

**Администрирование**
- Панель администратора
- Управление инвайт-кодами и пользователями

---

## Структура репозитория

```
├── app/                    # Бэкенд
│   ├── core/               # Конфиг, БД, JWT, Redis
│   ├── models/             # SQLAlchemy модели
│   ├── repositories/       # Слой доступа к БД
│   ├── services/           # Бизнес-логика
│   ├── routers/            # FastAPI эндпоинты
│   ├── ws/                 # WebSocket менеджер + Redis Pub/Sub
│   └── crypto/             # AES-GCM шифрование
├── alembic/                # Миграции БД
├── tests/                  # pytest: auth, chats, ws, media, security...
├── frontend/               # Фронтенд
│   └── src/
│       ├── components/     # ChatWindow, Sidebar, MessageItem...
│       ├── pages/          # ChatPage, GroupsPage, ContactsPage, LoginPage
│       ├── services/       # API-клиент
│       ├── store/          # Zustand store
│       └── hooks/          # useWebSocket, useMediaUpload, useNotifications
├── deploy/                 # nginx конфиг и скрипт деплоя
├── Dockerfile              # Multi-stage, Alpine
├── docker-compose.yml      # Локальная разработка
└── docker-compose.prod.yml # Продакшн
```

---

## Локальный запуск

```bash
bash setup_local.sh
```

Скрипт: создаст `.env`, сгенерирует секреты, поднимет PostgreSQL и Redis в Docker, накатит миграции, запустит uvicorn с hot reload.

Бэкенд: http://localhost:8000  
Swagger: http://localhost:8000/docs

Фронтенд (отдельно):
```bash
cd frontend
npm install
npm run dev   # http://localhost:5173
```

По умолчанию фронт смотрит на `http://localhost:8000`. Переопределяется через:
```bash
VITE_API_URL=http://localhost:8000
```

---

## Переменные окружения

```bash
cp .env.example .env
```

| Переменная | Обязательно | Описание |
|---|---|---|
| `DATABASE_URL` | ✓ | PostgreSQL async URL |
| `POSTGRES_USER` | ✓ | Пользователь БД |
| `POSTGRES_PASSWORD` | ✓ | Пароль БД |
| `POSTGRES_DB` | ✓ | Имя БД |
| `JWT_SECRET` | ✓ | Секрет подписи токенов |
| `JWT_EXPIRE_MINUTES` | — | TTL access-токена (по умолчанию: 60) |
| `CRYPTO_KEY` | ✓ | 32 байта в hex (64 символа) для AES-GCM |
| `CRYPTO_BACKEND` | — | Бэкенд шифрования (по умолчанию: `aes`) |
| `ADMIN_USERNAME` | — | Логин администратора (по умолчанию: `admin`) |
| `REDIS_URL` | — | URL Redis (по умолчанию: `redis://localhost:6379`) |
| `MEDIA_DIR` | — | Путь к медиахранилищу (по умолчанию: `/app/media`) |
| `MEDIA_MAX_UPLOAD_MB` | — | Максимальный размер загрузки (по умолчанию: 20) |
| `MEDIA_TTL_DAYS` | — | Дней до удаления старых медиафайлов (по умолчанию: 365) |

Сгенерировать секреты:
```bash
openssl rand -hex 32  # для JWT_SECRET и CRYPTO_KEY
```

---

## Миграции

```bash
# Создать
alembic revision --autogenerate -m "описание"

# Применить
alembic upgrade head
```

---

## Тесты

```bash
pytest
```

Покрытие: авторизация и refresh-токены, регистрация и инвайты, чаты (личные и групповые), сообщения, контакты и блокировки, медиафайлы и очистка, emoji, WebSocket-тикеты, rate limiting, целостность данных при удалении пользователей.

---

## Деплой на VPS

> ⚠️ Процесс деплоя в процессе переработки.

Текущая схема: сборка Docker-образа локально → rsync архива на VPS → рестарт стека.

Настрой `deploy/deploy.sh`:
```bash
REMOTE_USER="your_vps_user"
REMOTE_HOST="your.vps.ip"
REMOTE_DIR="/home/your_vps_user/messenger"
SSH_KEY="$HOME/.ssh/your_key"
DOMAIN="your-domain.example.com"
```

```bash
bash deploy/deploy.sh             # полный деплой (сборка + загрузка + рестарт)
bash deploy/deploy.sh --no-build  # только рестарт
```

---

## Лицензия

MIT
