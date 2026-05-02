# ── Stage 1: Сборка ──────────────────────────────────────────
FROM python:3.12-alpine AS builder

# Установка зависимостей для сборки (удаляем после использования)
RUN apk add --no-cache \
    gcc musl-dev libffi-dev \
    jpeg-dev zlib-dev

WORKDIR /app

# 1. Сначала обновляем pip и ставим зависимости (этот слой кэшируется)
RUN pip install --no-cache-dir --upgrade pip
COPY requirements.txt .
RUN pip install --no-cache-dir \
    --root-user-action=ignore \
    --prefix=/install -r requirements.txt

# ── Stage 2: Финальный образ ──────────────────────────────────
FROM python:3.12-alpine

# Настройки для Python:
# 1. Не писать .pyc файлы.
# 2. Моментальный вывод логов в консоль (важно для Docker)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/usr/local/bin:$PATH"

RUN apk add --no-cache libjpeg libstdc++

WORKDIR /app

# Копируем только установленные библиотеки
COPY --from=builder /install /usr/local
# Копируем код приложения (этот слой меняется часто)
COPY . .

# Настройка прав
RUN adduser -D appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
