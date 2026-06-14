FROM node:22-alpine AS builder
WORKDIR /app

# Копируем файлы зависимостей и устанавливаем их
COPY package*.json ./
RUN npm config set legacy-peer-deps true && npm ci

# Копируем исходный код
COPY . .
RUN NODE_OPTIONS="--max-old-space-size=400" npm run build

# Финальный легковесный образ
FROM alpine:latest
COPY --from=builder /app/dist /build
CMD ["tail", "-f", "/dev/null"]
