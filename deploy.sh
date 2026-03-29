#!/usr/bin/env bash
# ============================================================
#  Деплой messenger-backend на VPS
#  Использование:
#    bash deploy/deploy.sh              # полный деплой
#    bash deploy/deploy.sh --no-build   # только рестарт (без сборки)
# ============================================================
set -euo pipefail

# ── Настройки ─────────────────────────────────────────────────────────────
IMAGE="messenger-backend"
REMOTE_USER="your_vps_user"
REMOTE_HOST="your.vps.ip"
REMOTE_DIR="/home/your_vps_user/messenger"
SSH_KEY="$HOME/.ssh/your_key"
DOMAIN="your-domain.example.com"
APP_PORT="8000"
# ──────────────────────────────────────────────────────────────────────────

SSH="ssh $REMOTE_USER@$REMOTE_HOST"
ARCHIVE="messenger.tar.gz"
NO_BUILD=false

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
ok()   { echo -e "${GREEN}  ✓ $*${NC}"; }
info() { echo -e "${CYAN}  → $*${NC}"; }
warn() { echo -e "${YELLOW}  ⚠ $*${NC}"; }
die()  { echo -e "${RED}  ✗ $*${NC}"; exit 1; }

for arg in "$@"; do [[ "$arg" == "--no-build" ]] && NO_BUILD=true; done

echo -e "\n${CYAN}╔══════════════════════════════════════════╗"
echo -e "║   messenger-backend  deploy             ║"
echo -e "╚══════════════════════════════════════════╝${NC}\n"

# ── Интерактивный вопрос (пропускается если передан флаг) ─────────────────
if [[ "$NO_BUILD" == false ]]; then
  # Показываем когда последний раз собирали образ
  LAST_BUILD=$(docker inspect --format='{{.Created}}' messenger-backend:latest 2>/dev/null \
    | cut -c1-19 | tr 'T' ' ' || echo "никогда")
  echo -e "${CYAN}  Последняя сборка образа: ${YELLOW}${LAST_BUILD}${NC}"
  echo -e "${CYAN}  Пересобрать Docker образ?${NC}"
  echo -e "    ${GREEN}y${NC} — собрать и загрузить новый образ"
  echo -e "    ${YELLOW}n${NC} — использовать уже загруженный на сервере"
  echo ""
  read -r -p "  [y/N]: " BUILD_ANSWER
  case "$BUILD_ANSWER" in
    [yY][eE][sS]|[yY]) NO_BUILD=false ;;
    *) NO_BUILD=true; warn "Пропускаем сборку — используем образ на сервере" ;;
  esac
  echo ""
fi

# ── Проверки ──────────────────────────────────────────────────────────────
[[ -f ".env" ]]       || die ".env не найден — скопируй .env.example и заполни"
[[ -f "Dockerfile" ]] || die "Dockerfile не найден — запусти из корня проекта"
[[ -f "$SSH_KEY" ]]   || die "SSH ключ не найден: $SSH_KEY"
command -v docker >/dev/null || die "docker не установлен"
command -v rsync  >/dev/null || die "rsync не установлен"

# ── SSH-agent (один раз вводим парольную фразу ключа) ─────────────────────
info "Запускаем ssh-agent..."
eval "$(ssh-agent -s)" > /dev/null
trap 'ssh-agent -k > /dev/null' EXIT
ssh-add "$SSH_KEY"
ok "Ключ добавлен в агент"

# ── Сборка и загрузка образа ──────────────────────────────────────────────
if [[ "$NO_BUILD" == false ]]; then
  info "Сборка Docker образа..."
  docker build --network=host -t $IMAGE . || die "Сборка провалилась"
  ok "Образ собран: $IMAGE"

  info "Упаковка образа..."
  docker save $IMAGE | gzip > $ARCHIVE
  ok "Архив готов: $ARCHIVE ($(du -sh $ARCHIVE | cut -f1))"

  info "Загрузка образа на сервер..."
  rsync -az --progress -e ssh \
    $ARCHIVE $REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/
  ok "Образ загружен"
  rm -f $ARCHIVE
else
  warn "--no-build: пропускаем сборку и загрузку образа"
fi

# ── Синхронизация конфигов ────────────────────────────────────────────────
info "Синхронизируем конфиги..."
$SSH "mkdir -p $REMOTE_DIR"
rsync -az -e ssh \
  docker-compose.prod.yml \
  .env \
  deploy/nginx_vps.conf \
  $REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/
ok "Конфиги синхронизированы"

# ── Всё остальное на сервере ──────────────────────────────────────────────
info "Запускаем деплой на сервере..."
$SSH bash << ENDSSH
  set -euo pipefail
  cd $REMOTE_DIR

  # ── Секреты (генерируем один раз, потом только читаем) ──────────────────
  SECRET_FILE="$REMOTE_DIR/.jwt-secret"
  CRYPTO_FILE="$REMOTE_DIR/.crypto-key"

  if [ ! -f "\$SECRET_FILE" ]; then
    echo "  → Генерация JWT_SECRET (первый запуск)..."
    openssl rand -hex 32 > "\$SECRET_FILE" && chmod 600 "\$SECRET_FILE"
  fi
  if [ ! -f "\$CRYPTO_FILE" ]; then
    echo "  → Генерация CRYPTO_KEY (первый запуск)..."
    openssl rand -hex 32 > "\$CRYPTO_FILE" && chmod 600 "\$CRYPTO_FILE"
  fi

  sed -i "s|^JWT_SECRET=.*|JWT_SECRET=\$(cat \$SECRET_FILE)|" .env
  sed -i "s|^CRYPTO_KEY=.*|CRYPTO_KEY=\$(cat \$CRYPTO_FILE)|"  .env

  # ── Загружаем новый образ ───────────────────────────────────────────────
  if [ -f "$REMOTE_DIR/$ARCHIVE" ]; then
    echo "  → Загрузка образа..."
    docker load < $REMOTE_DIR/$ARCHIVE
    rm -f $REMOTE_DIR/$ARCHIVE
    echo "  ✓ Образ загружен"
  fi

  # ── Docker стек ─────────────────────────────────────────────────────────
  echo "  → Остановка старого стека..."
  docker-compose -f docker-compose.prod.yml down --remove-orphans 2>/dev/null || true

  echo "  → Запуск..."
  docker-compose -f docker-compose.prod.yml up -d

  echo "  → Статус:"
  docker-compose -f docker-compose.prod.yml ps

  # ── Nginx + сертификат ──────────────────────────────────────────────────
  echo "  → Настройка nginx..."

  sudo -n ln -sf /etc/nginx/sites-available/messenger /etc/nginx/sites-enabled/messenger

  CERT_DIR="/etc/letsencrypt/live/$DOMAIN"
  if [ ! -d "\$CERT_DIR" ]; then
    echo "  → Выпускаем сертификат (временный HTTP конфиг)..."

    # Шаг 1: временный конфиг только с HTTP — nginx стартует без сертификата
    sudo -n tee /etc/nginx/sites-available/messenger > /dev/null << 'NGINX_TMP'
server {
    listen 80;
    server_name $DOMAIN;
    location / {
        proxy_pass http://127.0.0.1:$APP_PORT;
    }
}
NGINX_TMP

    sudo -n nginx -t && sudo -n systemctl reload nginx

    # Шаг 2: выпускаем сертификат через webroot/standalone
    sudo -n certbot certonly --nginx -d $DOMAIN --non-interactive --agree-tos \
      -m admin@$DOMAIN 2>&1 | tail -5
    echo "  ✓ Сертификат выпущен"
  else
    echo "  ✓ Сертификат уже есть, пропускаем"
  fi

  # Финальный конфиг с HTTPS — берём из репозитория
  sudo -n cp $REMOTE_DIR/nginx_vps.conf /etc/nginx/sites-available/messenger

  sudo -n nginx -t && sudo -n systemctl reload nginx
  echo "  ✓ nginx перезагружен"

  # ── Health check ────────────────────────────────────────────────────────
  echo "  → Health check..."
  sleep 2
  STATUS=\$(curl -sf -o /dev/null -w "%{http_code}" http://localhost:$APP_PORT/docs || echo "000")
  if [ "\$STATUS" == "200" ]; then
    echo "  ✓ Приложение отвечает (HTTP \$STATUS)"
  else
    echo "  ⚠ HTTP \$STATUS — смотри логи:"
    echo "    docker-compose -f docker-compose.prod.yml logs --tail=30 app"
  fi
ENDSSH

echo ""
echo -e "${CYAN}══════════════════════════════════════════${NC}"
echo -e "${GREEN}  Деплой завершён!${NC}"
echo -e "${CYAN}  Сайт:   ${NC}https://$DOMAIN"
echo -e "${CYAN}  Docs:   ${NC}https://$DOMAIN/docs"
echo -e "${CYAN}  Логи:   ${NC}ssh -i $SSH_KEY $REMOTE_USER@$REMOTE_HOST \\"
echo -e "           'cd $REMOTE_DIR && docker-compose -f docker-compose.prod.yml logs -f app'"
echo -e "${CYAN}══════════════════════════════════════════${NC}\n"
