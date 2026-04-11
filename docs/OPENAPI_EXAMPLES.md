# Примеры использования API (curl) и импорт в Postman

Ниже — быстрые curl-примеры для основных эндпойнтов. Замените `YOUR_API_KEY` и `BASE_URL` на ваши значения.

## Переменные
- `BASE_URL` — базовый адрес сервера, например `http://localhost:8000`
- `INTERNAL_API_KEY` — внутренний ключ, обязателен для всех запросов

## Natal (натальная карта)
```bash
curl -X POST "$BASE_URL/natal" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $INTERNAL_API_KEY" \
  -d '{"date":"1987-05-15","time":"13:45:00","tz":"+03:00","lat":59.93,"lon":30.36}'
```

## Synastry (синастрия)
```bash
curl -X POST "$BASE_URL/synastry" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $INTERNAL_API_KEY" \
  -d '{"person1":{"date":"1987-05-15","time":"13:45:00","tz":"+03:00","lat":59.93,"lon":30.36},"person2":{"date":"1990-10-01","time":"08:30:00","tz":"+02:00","lat":48.85,"lon":2.35}}'
```

## Horary (гороскоп-вопрос)
```bash
curl -X POST "$BASE_URL/horary" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $INTERNAL_API_KEY" \
  -d '{"lat":59.93,"lon":30.36,"question":"Will I get the job?","dt_utc":"2026-04-11T12:30:00Z"}'
```

## Solar Return (соляр)
```bash
curl -X POST "$BASE_URL/solar" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $INTERNAL_API_KEY" \
  -d '{"user_data":{"date":"1987-05-15","time":"13:45:00","tz":"+03:00","lat":59.93,"lon":30.36},"year":2026}'
```

## Natal (web) — только JSON
```bash
curl -X POST "$BASE_URL/natal_web" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $INTERNAL_API_KEY" \
  -d '{"name":"User","date":"1987-05-15","time":"13:45:00","tz":"+03:00","lat":59.93,"lon":30.36,"house_system":"P"}'
```

## Natal (SVG) — получить SVG как строку
```bash
curl -X POST "$BASE_URL/natal_svg" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $INTERNAL_API_KEY" \
  -d '{"name":"User","date":"1987-05-15","time":"13:45:00","tz":"+03:00","lat":59.93,"lon":30.36}'
```

## Predict - Daily (transits)
```bash
curl -X POST "$BASE_URL/predict/daily" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $INTERNAL_API_KEY" \
  -d '{"date":"1987-05-15","time":"13:45:00","tz":"+03:00","lat":59.93,"lon":30.36,"target_date":"2026-05-01"}'
```

## Predict - Ephemeris (graphical)
```bash
curl -X POST "$BASE_URL/predict/ephemeris" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $INTERNAL_API_KEY" \
  -d '{"name":"User","date":"1987-05-15","time":"13:45:00","tz":"+03:00","lat":59.93,"lon":30.36,"start_date":"2026-01-01","end_date":"2026-12-31","step_days":7}'
```

## Geo — Astrocartography Full
```bash
curl -X POST "$BASE_URL/geo/astrocartography-full" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $INTERNAL_API_KEY" \
  -d '{"name":"User","date":"1987-05-15","time":"13:45:00","tz":"+03:00","lat":59.93,"lon":30.36}'
```

## Geo — Astrocartography (lines only)
```bash
curl -X POST "$BASE_URL/geo/astrocartography" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $INTERNAL_API_KEY" \
  -d '{"name":"User","date":"1987-05-15","time":"13:45:00","tz":"+03:00","lat":59.93,"lon":30.36}'
```

## Geo — Local Space (lines)
```bash
curl -X POST "$BASE_URL/geo/local-space" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $INTERNAL_API_KEY" \
  -d '{"name":"User","date":"1987-05-15","time":"13:45:00","tz":"+03:00","lat":59.93,"lon":30.36}'
```

## Geo — Evaluate City
```bash
curl -X POST "$BASE_URL/geo/evaluate_city" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $INTERNAL_API_KEY" \
  -d '{"name":"User","date":"1987-05-15","time":"13:45:00","tz":"+03:00","lat":59.93,"lon":30.36,"target_lat":48.85,"target_lon":2.35,"city_name":"Paris"}'
```

## Geo — Evaluate Cities Bulk
```bash
curl -X POST "$BASE_URL/geo/evaluate_cities_bulk" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $INTERNAL_API_KEY" \
  -d '{"name":"User","date":"1987-05-15","time":"13:45:00","tz":"+03:00","lat":59.93,"lon":30.36,"coordinates":[[48.85,2.35],[40.71,-74.0]]}'
```

## Geo — Check Point / Check Local Space Point
```bash
curl -X POST "$BASE_URL/geo/check_point" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $INTERNAL_API_KEY" \
  -d '{"name":"User","date":"1987-05-15","time":"13:45:00","tz":"+03:00","lat":59.93,"lon":30.36,"target_lat":48.85,"target_lon":2.35,"target_name":"Paris spot"}'
```

```bash
curl -X POST "$BASE_URL/geo/check-local-point" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $INTERNAL_API_KEY" \
  -d '{"name":"User","date":"1987-05-15","time":"13:45:00","tz":"+03:00","lat":59.93,"lon":30.36,"target_lat":48.85,"target_lon":2.35,"target_name":"Paris local"}'
```

## Geo — Local Space Chart
```bash
curl -X POST "$BASE_URL/geo/local-space-chart" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $INTERNAL_API_KEY" \
  -d '{"name":"User","date":"1987-05-15","time":"13:45:00","tz":"+03:00","lat":59.93,"lon":30.36}'
```

## Импорт Postman-коллекции
1. Откройте Postman → File → Import → выберите `docs/postman_collection.json`.
2. В настройках коллекции задайте переменные окружения `baseUrl` и `INTERNAL_API_KEY`.
3. Отправляйте запросы из коллекции.

## OpenAPI
- Приложение на FastAPI генерирует OpenAPI спецификацию автоматически в рантайме по адресу: `$BASE_URL/openapi.json`.
- Вы можете импортировать `openapi.json` в Postman или Swagger UI для автодокументации и тестирования.


Если хотите, я могу:
- сгенерировать полноценный `openapi.yaml` (на основе рантайм-`openapi.json`, если вы запустите сервис),
- или расширить коллекцию Postman добавлением эндпойнтов `predict`, `geo` и т.д.
