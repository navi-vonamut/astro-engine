# Документация роутов: `synastry`, `horary`, `solar`

Этот документ описывает входные данные, поведение, примеры запросов и ожидаемые ответы для маршрутов, связанных с синатрией, гороскопом вопроса и соляром.

Общие требования
- Все роуты защищены внутренним ключом `X-API-Key` (см. `app/deps.py`).
- Форматы дат/времён и координат — как в `app/schemas.py` и `app/engine/core/models.py`.

---

## POST /synastry
- Файл: `app/routes/synastry.py`
- Описание: рассчитывает синастрию двух людей — возвращает синатрические аспекты и наложения планет в домах партнёра.
- Auth: `X-API-Key: <INTERNAL_API_KEY>`

Вход (пример):
```json
{
  "person1": {"date":"1987-05-15","time":"13:45:00","tz":"+03:00","lat":59.93,"lon":30.36},
  "person2": {"date":"1990-10-01","time":"08:30:00","tz":"+02:00","lat":48.85,"lon":2.35}
}
```

Поведение:
- На сервере `SynastryRequest` конвертируется в два `BirthInput` и передаётся в `KerykeionEngine.synastry`.
- Результат содержит:
  - `meta` — `{ type: "synastry", p1: <name>, p2: <name> }`
  - `aspects` — список синатрических аспектов (каждый `{ person1_object, aspect, person2_object, orb }`)
  - `overlays` — объект с `owner_planets_in_partner_houses` и `partner_planets_in_owner_houses` (каждый элемент `{ planet, in_partner_house, partner_house_sign }`)

Пример ответ (сокращённый):
```json
{
  "meta": {"type":"synastry","p1":"Owner","p2":"Partner"},
  "aspects": [{"person1_object":"Venus","aspect":"Trine","person2_object":"Moon","orb":1.23}],
  "overlays": {"owner_planets_in_partner_houses":[{"planet":"Sun","in_partner_house":10}] , "partner_planets_in_owner_houses":[] }
}
```

Ошибки: 401 — неверный `X-API-Key`; 500 — внутренняя ошибка расчёта.

---

## POST /horary
- Файл: `app/routes/horary.py`
- Описание: создаёт гороскоп вопроса по переданному UTC-времени и координатам точки.
- Auth: `X-API-Key`

Вход (пример):
```json
{
  "lat": 59.93,
  "lon": 30.36,
  "question": "Will I get the job?",
  "dt_utc": "2026-04-11T12:30:00Z"
}
```

Поведение:
- `dt_utc` парсится как ISO формат UTC; затем конвертируется в `BirthInput` с `tz="+00:00"` и передаётся в `KerykeionEngine.horary(inp, question)`.
- Метод `horary` возвращает структуру, похожую на `natal`, но с `meta.type = "horary"` и `meta.question` = текст вопроса. Также добавляется поле `is_combust` для планет (расчёт комбустности относительно Солнца).

Пример ответа (сокращённый):
```json
{
  "meta": {"type":"horary","subject":"Querent","datetime":"2026-04-11T12:30:00","question":"Will I get the job?"},
  "planets": [{"name":"Sun","abs_pos":...},{"name":"Moon","abs_pos":...}],
  "aspects": [...],
  "planet_status": {...}
}
```

Ошибки: 400 — неверный формат `dt_utc` (будет выброшено при парсинге), 401/500 как обычно.

---

## POST /solar
- Файл: `app/routes/solar.py`
- Описание: рассчитывает соляр (solar return) для заданного года и, опционально, локации возвращения.
- Auth: `X-API-Key`

Вход (пример):
```json
{
  "user_data": {"date":"1987-05-15","time":"13:45:00","tz":"+03:00","lat":59.93,"lon":30.36},
  "year": 2026,
  "return_lat": 56.84,
  "return_lon": 60.61,
  "return_tz": "+05:00"
}
```

Поведение:
- Формирует `natal_inp` из `user_data`.
- Если `return_lat/return_lon` не заданы, использует координаты рождения.
- Вызывает `KerykeionEngine.solar_return(natal_inp, year, loc_lat, loc_lon, loc_tz)`.
- Результат — структура натальной карты для момента Соляра с добавленным `meta.type = "solar_return"`, `meta.solar_year` и `meta.location_name`.

Пример ответа (сокращённый):
```json
{
  "meta": {"type":"solar_return","solar_year":2026,"location_name":"56.84,60.61"},
  "planets": [...],
  "aspects": [...],
  "dominants": {...}
}
```

Ошибки: 401/500.

---

## Реализация защищённого доступа (X-API-Key)
- В `app/config.py` `SETTINGS.internal_api_key` берётся из `INTERNAL_API_KEY`.
- Если не задан, `verify_internal_api_key` будет возвращать HTTP 500 с сообщением "INTERNAL_API_KEY is not configured".

---

## Рекомендации по использованию фронтендом
- Отдавать большие структуры (натал, соляр) не переводя в SVG (для `/natal_web`) — фронтенд обязан рендерить данные оптимально.
- Для `/natal_svg` и других роутов, возвращающих SVG в теле JSON, фронтенд должен вставлять SVG через безопасные механизмы или запрашивать его как `image/svg+xml`.

---

Сохранено в `docs/ROUTES.md`.
