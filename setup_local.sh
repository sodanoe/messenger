#!/usr/bin/env bash
# ============================================================
#  Локальный запуск messenger-backend
#  Использование: bash setup_local.sh
# ============================================================
set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { echo -e "${GREEN}  ✓ $*${NC}"; }
info() { echo -e "${CYAN}  → $*${NC}"; }
warn() { echo -e "${YELLOW}  ⚠ $*${NC}"; }
die()  { echo -e "${RED}  ✗ $*${NC}"; exit 1; }

echo -e "\n${CYAN}╔══════════════════════════════════════════╗"
echo -e "║   messenger-backend  local setup        ║"
echo -e "╚══════════════════════════════════════════╝${NC}\n"

# ── Проверки зависимостей ─────────────────────────────────────────────────
command -v docker  >/dev/null || die "docker не установлен"
command -v python3 >/dev/null || die "python3 не установлен"
ok "Зависимости найдены"

# ── .env ──────────────────────────────────────────────────────────────────
if [[ -f ".env" ]]; then
  warn ".env уже существует, пропускаем создание"
else
  info "Создаём .env..."
  cp .env.example .env

  # Генерируем секреты автоматически
  JWT_SECRET=$(openssl rand -hex 32)
  CRYPTO_KEY=$(openssl rand -hex 32)

  sed -i "s|change_me_use_openssl_rand_hex_32|${JWT_SECRET}|1" .env
  sed -i "s|change_me_use_openssl_rand_hex_32|${CRYPTO_KEY}|1" .env

  # Спрашиваем пароль БД
  echo ""
  echo -e "${CYAN}  Пароль для PostgreSQL (Enter = оставить 'change_me'):${NC}"
  read -r -p "  > " PG_PASS
  if [[ -n "$PG_PASS" ]]; then
    sed -i "s|POSTGRES_PASSWORD=change_me|POSTGRES_PASSWORD=${PG_PASS}|" .env
    # Обновляем и в DATABASE_URL
    sed -i "s|postgresql+asyncpg://user:password@|postgresql+asyncpg://messenger:${PG_PASS}@|" .env
  else
    warn "Используем дефолтный пароль 'change_me' — только для локальной разработки"
    sed -i "s|postgresql+asyncpg://user:password@|postgresql+asyncpg://messenger:change_me@|" .env
    sed -i "s|POSTGRES_PASSWORD=change_me|POSTGRES_PASSWORD=change_me|" .env
  fi

  ok ".env создан"
fi

# ── Docker (только db + redis) ────────────────────────────────────────────
info "Запускаем PostgreSQL и Redis..."
docker compose up -d db redis
ok "Контейнеры запущены"

# ── Ждём готовности БД ────────────────────────────────────────────────────
info "Ждём готовности PostgreSQL..."
for i in {1..20}; do
  if docker compose exec db pg_isready -U messenger &>/dev/null; then
    ok "PostgreSQL готов"
    break
  fi
  sleep 1
  if [[ $i == 20 ]]; then
    die "PostgreSQL не ответил за 20 секунд"
  fi
done

# ── Python зависимости ────────────────────────────────────────────────────
if [[ ! -d ".venv" ]]; then
  info "Создаём виртуальное окружение..."
  python3 -m venv .venv
  ok "venv создан"
fi

info "Устанавливаем зависимости..."
.venv/bin/pip install -q -r requirements.txt
ok "Зависимости установлены"

# ── Миграции ──────────────────────────────────────────────────────────────
info "Накатываем миграции..."
set -a; source .env; set +a
.venv/bin/alembic upgrade head
ok "Миграции применены"

# ── Запуск ────────────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}══════════════════════════════════════════${NC}"
echo -e "${GREEN}  Всё готово! Запускаем сервер...${NC}"
echo -e "${CYAN}  http://localhost:8000${NC}"
echo -e "${CYAN}  http://localhost:8000/docs${NC}"
echo -e "${CYAN}══════════════════════════════════════════${NC}\n"

.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
