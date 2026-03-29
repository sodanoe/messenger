# ── Stage 1: сборка зависимостей ──────────────────────────────
FROM python:3.12-alpine AS builder

# Системные либы нужны только для компиляции Pillow и cryptography
RUN apk add --no-cache \
    gcc musl-dev libffi-dev \
    jpeg-dev zlib-dev

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: финальный образ ───────────────────────────────────
FROM python:3.12-alpine

# Только рантайм-либы (без gcc и dev-заголовков)
RUN apk add --no-cache libjpeg libstdc++

WORKDIR /app
COPY --from=builder /install /usr/local
COPY . .

RUN adduser -D appuser
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]