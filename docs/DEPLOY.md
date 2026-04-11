# Deploy — astro-engine

Переменные окружения
- `INTERNAL_API_KEY` — обязательный секрет для доступа к API.
- Другие переменные: см. `Dockerfile` и `docker-compose.yml` при необходимости.

Локальная разработка

```bash
# Установить зависимости
pip install -r requirements.txt

# Установить ключ (PowerShell)
$env:INTERNAL_API_KEY = "your_secret_key"

# Запуск
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Docker
- В репозитории присутствуют `Dockerfile` и `docker-compose.yml`.
- Пример файла `.env`:

```
INTERNAL_API_KEY=your_secret_key
PORT=8000
```

Запуск с Docker Compose

```bash
docker-compose up --build -d
```

Проверка
- Swagger UI: `http://<host>:<port>/docs`
- Логи: `docker-compose logs -f`

Рекомендации для продакшена
- Использовать `uvicorn` под `gunicorn`/`uvicorn.workers.UvicornWorker` или контейнеризованный сервис с прокси (nginx).
- Хранить секреты в безопасном хранилище (Vault, секреты облака) или в переменных окружения CI.
- Настроить ограничение запросов и мониторинг (Prometheus/Alerting).
