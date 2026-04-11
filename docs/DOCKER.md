# Docker / Deployment

Документация по сборке и запуску сервиса в контейнере Docker, а также по работе с `docker-compose` и окружением.

## Коротко
- Образ собирается из `Dockerfile` в корне репозитория.
- Для запуска в контейнере требуется передать переменные окружения, в том числе `INTERNAL_API_KEY`.
- В продакшене рекомендуется использовать `docker-compose` или оркестратор и проксировать трафик через Nginx / Traefik.

## Требования
- Python зависимости из `requirements.txt`.
- Нативные зависимости для `swisseph`/`kerykeion` (если используются) — могут потребоваться системные пакеты (например, `build-essential`, `libc-dev` и т.д.).

## Пример `Dockerfile` (рекомендованный)

Многоступенчатая сборка для уменьшения размера образа:

```dockerfile
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt ./
RUN pip install --upgrade pip && pip wheel --wheel-dir /wheels -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /wheels /wheels
RUN pip install --no-index --find-links=/wheels -r requirements.txt
COPY . /app
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
```

Если ваш стек требует системных пакетов (например, для `swisseph`), добавьте их в образ перед `pip install`:
```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libatlas-base-dev libgfortran5 && rm -rf /var/lib/apt/lists/*
```

## Собрать образ и запустить

Собрать локально:
```bash
docker build -t astro-engine:latest .
```

Запустить контейнер:
```bash
docker run -e INTERNAL_API_KEY="your-secret" -p 8000:8000 astro-engine:latest
```

Совет: для разработки монтируйте код в контейнер и используйте `uvicorn --reload`.

## `docker-compose.yml` (пример)

```yaml
version: '3.8'
services:
  astro:
    build: .
    ports:
      - "8000:8000"
    environment:
      - INTERNAL_API_KEY=${INTERNAL_API_KEY}
    volumes:
      - ./:/app:ro
    restart: unless-stopped

# При необходимости можно добавить сервисы для БД, кеша и т.п.
```

Запуск через `docker-compose`:
```bash
export INTERNAL_API_KEY="your-secret"
docker-compose up --build -d
```

## Переменные окружения (обязательные/рекомендуемые)
- `INTERNAL_API_KEY` — обязательно, используется в `app/deps.py` для валидации внутренних запросов.
- `LOG_LEVEL` — опционально (`info`, `debug`).
- `SWISSEPH_PATH` — если требуется указать путь к файлам эфемерид.

Хранение секретов
- Не храните `INTERNAL_API_KEY` в образе. Передавайте через CI/CD секреты, переменные окружения в оркестраторе, HashiCorp Vault или Docker secrets.

## Работа с нативными зависимостями
- `swisseph` и/или `kerykeion` могут требовать нативных библиотек. Если при установке зависимостей в контейнере возникают ошибки сборки, установите необходимые системные пакеты (см. пример `apt-get` выше).

## Healthcheck
Рекомендуется добавить `HEALTHCHECK` в `Dockerfile` или в `docker-compose` для проверки `/health`:

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s CMD curl -f http://localhost:8000/health || exit 1
```

## Монтирование временных директорий
- Если сервер генерирует SVG или временные файлы, убедитесь, что в контейнере есть доступная временная директория (обычно `/tmp`). При необходимости монтируйте внешний том для сохранения артефактов.

## Production рекомендации
- Используйте реверс-прокси (Nginx/Traefik) перед Uvicorn.
- Включите логирование и мониторинг (Prometheus, Sentry).
- Разделяйте окружения (`.env` для dev, CI/CD secrets для prod).

## Отладка
- Для интерактивной отладки запустите контейнер с шеллом:
```bash
docker run -it --entrypoint /bin/bash -e INTERNAL_API_KEY="..." astro-engine:latest
```

## Заключение
Документация по Docker даёт базовый набор сценариев для сборки и запуска сервиса. Если хотите, могу:
- добавить `docker-compose.override.yml` для разработки;
- подготовить `Dockerfile` с уже добавленными системными зависимостями конкретно для `swisseph` (укажите дистрибутив и ошибки, если есть).
