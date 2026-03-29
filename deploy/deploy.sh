#!/usr/bin/env bash
# Запускать на VPS в папке с проектом
set -e

echo "⏳  Pulling latest changes..."
# Если используешь git: git pull origin main

echo "⏳  Building & restarting containers..."
docker compose -f docker-compose.prod.yml --env-file .env up -d --build

echo "⏳  Running migrations..."
docker compose -f docker-compose.prod.yml exec app alembic upgrade head

echo "✅  Done! App is running on 127.0.0.1:8000"
