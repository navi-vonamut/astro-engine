# astro-engine — Документация

Краткое описание
- Лёгкий FastAPI сервис для астрологических расчётов, использует внутренний движок `kerykeion`.
- Основные маршруты: `natal`, `predict`, `synastry`, `horary`, `solar`, `geo`.

Быстрый старт

1) Установите зависимости:

```bash
pip install -r requirements.txt
```

2) Экспортируйте ключ API (обязательно):

```bash
export INTERNAL_API_KEY="your_secret_key"
# Windows PowerShell
$env:INTERNAL_API_KEY = "your_secret_key"
```

3) Запустите локально через Uvicorn:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

4) Swagger UI: http://localhost:8000/docs

Docker (рекомендуется для продакшен-проверки)

```bash
docker-compose up --build
```

Где смотреть код
- Точки входа: [app/main.py](app/main.py)
- Схемы запросов: [app/schemas.py](app/schemas.py)
- Проверка API-ключа: [app/deps.py](app/deps.py)

Дальше: смотрите `API_REFERENCE.md`, `DEPLOY.md` и `EXAMPLES.md` в этой папке.
