
# Messenger API

Простое и эффективное API для мессенджера с поддержкой WebSocket для реального времени.

## Особенности

- ✅ Аутентификация через JWT
- 💬 Поддержка групповых и приватных чатов
- 🔄 WebSocket для мгновенных сообщений
- 📱 Полноценный REST API
- 🛡️ Ролевая система (владелец/участник)
- 📊 Статусы пользователей онлайн/оффлайн

## Технологии

- Python 3.10+
- FastAPI
- SQLAlchemy (ORM)
- WebSockets
- JWT (аутентификация)
- Pydantic (валидация данных)

## Установка

1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/your-repo/messenger-api.git
   cd messenger-api
   ```

2. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```

3. Настройте переменные окружения (создайте `.env` файл):
   ```ini
   PROJECT_NAME=MessengerAPI
   DESCRIPTION=API для мессенджера
   VERSION=1.0.0
   DEBUG=True
   DATABASE_URL=postgresql://user:password@localhost:5432/messenger
   SECRET_KEY=your-secret-key-here
   ```

4. Запустите приложение:
   ```bash
   uvicorn src.app.main:app --reload
   ```

## API Endpoints

### Аутентификация
- `POST /auth/register` - Регистрация
- `POST /auth/login` - Вход
- `GET /auth/me` - Информация о текущем пользователе

### Чаты
- `POST /chats/create` - Создать чат
- `GET /chats/` - Список чатов пользователя
- `GET /chats/{chat_id}` - Информация о чате
- `POST /chats/{chat_id}/join` - Присоединиться к чату
- `DELETE /chats/{chat_id}/leave` - Покинуть чат

### Сообщения
- `POST /messages/send` - Отправить сообщение
- `GET /messages/chat/{chat_id}` - Получить сообщения из чата
- `PUT /messages/edit/{message_id}` - Редактировать сообщение
- `DELETE /messages/delete/{message_id}` - Удалить сообщение

### WebSocket
- `WS /ws/chat/{token}` - WebSocket соединение
- `GET /ws/online-users` - Список онлайн пользователей
- `GET /ws/chat/{chat_id}/online-users` - Онлайн пользователи в чате

## Модели данных

### Пользователь (User)
```python
id: int
username: str
email: str
hashed_password: str
is_active: bool
created_at: datetime
```

### Чат (Chat)
```python
id: int
name: str
description: str
is_group: bool
created_at: datetime
```

### Сообщение (Message)
```python
id: int
text: str
chat_id: int
author_id: int
created_at: datetime
is_edited: bool
```

## WebSocket Events

### Отправляемые события:
- `subscribe_chat` - Подписаться на чат
- `unsubscribe_chat` - Отписаться от чата
- `private_message` - Личное сообщение
- `typing` - Индикатор набора текста

### Получаемые события:
- `new_message` - Новое сообщение
- `message_edited` - Сообщение изменено
- `message_deleted` - Сообщение удалено
- `user_status` - Изменение статуса пользователя

## Примеры запросов

### Регистрация
```http
POST /auth/register
Content-Type: application/json

{
  "username": "testuser",
  "email": "test@example.com",
  "password": "securepassword123"
}
```

### Создание чата
```http
POST /chats/create
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Общий чат",
  "description": "Чат для всех участников",
  "is_group": true
}
```

## Тестирование

Для тестирования WebSocket можно использовать файл `websocket_test.html` или `websocket_test_new.html`:

1. Откройте файл в браузере
2. Введите JWT токен после авторизации
3. Подключитесь к WebSocket
4. Тестируйте функционал чата

## Лицензия

MIT
