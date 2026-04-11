# API Reference — astro-engine

Общие требования
- Все приватные эндпоинты защищены внутренним API ключом: заголовок `X-API-Key: <INTERNAL_API_KEY>`.
- Форматы даты: `YYYY-MM-DD` (или `YYYY/MM/DD`), время: `HH:MM:SS`, временная зона: `+03:00` или именованная `Europe/Warsaw`.

Эндпоинты

**GET /health**
- Описание: проверка состояния
- Ответ: `{ "status": "ok" }`

**GET /meta**
- Описание: мета-информация о движке
- Ответ: `{ "engine": "kerykeion", "engine_version": "5.6.0" }`

**POST /natal**
- Описание: базовый расчёт (JSON)
- Auth: `X-API-Key`
- Тело (пример):

```json
{
  "date": "1987-05-15",
  "time": "13:45:00",
  "tz": "+03:00",
  "lat": 59.9311,
  "lon": 30.3609
}
```
- Возвращает: JSON с данными расчёта (см. движок `KerykeionEngine`).

**POST /natal_web**
- Описание: расчёт для сайта — возвращает только данные (без SVG)
- Доп. поля: `name`, `house_system` (по умолчанию `P`), `node_type` (по умолчанию `true`)

**POST /natal_svg**
- Описание: генерирует отдельную SVG картинку
- Тело: как в `natal`, опционально `name` и `house_system`
- Возвращает: `{ "status": "success", "svg": "<svg>...</svg>" }`

**POST /predict/daily**
- Описание: транзиты/прогноз на указанную дату
- Тело (пример):

```json
{
  "date": "1987-05-15",
  "time": "13:45:00",
  "tz": "+03:00",
  "lat": 59.9311,
  "lon": 30.3609,
  "target_date": "2026-04-11"
}
```
- Возвращает: структура транзитов и аспектов (JSON)

**POST /predict/ephemeris**
- Описание: графическая эфемерида (серия точек)
- Тело: см. `EphemerisEngineRequest` в коде — содержит `start_date`, `end_date`, `step_days`.

Остальные маршруты
- `POST /synastry` — сравнение двух `NatalChartRequest` (см. `app/routes/synastry.py`).
- `POST /horary` — гороскоп вопроса (см. `app/routes/horary.py`).
- `POST /solar` — solar return (см. `app/routes/solar.py`).
- `POST /geo` — географические утилиты (см. `app/routes/geo.py`).

Ошибки и коды статуса
- `401 Unauthorized` — неверный `X-API-Key`
- `500` — внутренняя конфигурационная ошибка (например, не задан `INTERNAL_API_KEY`)

Дополнения
- Для точных форматов ответов смотрите реализацию в `app/engine/kerykeion_engine.py` и `app/engine/core/models.py`.
