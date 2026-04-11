# Входные и выходные поля — спецификация

Файл описывает структуры запросов и ответов для основных эндпоинтов.

Общие форматы
- Даты: строка `YYYY-MM-DD` или `YYYY/MM/DD`
- Время: строка `HH:MM:SS`
- Часовой пояс: строка, например `+03:00` или `Europe/Warsaw`

1) `POST /natal`, `POST /natal_web`, `POST /natal_svg`

Вход (на основе `NatalChartRequest`):
- `date` (string, required) — дата рождения
- `time` (string, required) — время рождения
- `tz` (string, required) — временная зона
- `lat` (number, required) — широта
- `lon` (number, required) — долгота
- `name` (string, optional, default "User") — имя субъекта
- `house_system` (string, optional, default "P") — система домов
- `node_type` (string, optional, default "true") — `true` или `mean` (только для `natal_web`)

Выход (`natal` / `natal_web` возвращают одинаковую структуру данных):
- `meta` (object):
  - `engine` (string)
  - `subject` (string)
  - `datetime` (string, ISO-like)
  - `location` (object: `lat`: number, `lon`: number)
  - `chart_ruler` (string | null)
- `planets` (array of objects): каждый элемент содержит поля:
  - `name` (string)
  - `sign` (string, short)
  - `sign_id` (int 0..11)
  - `degree` (number 0..30)
  - `abs_pos` (number 0..360)
  - `house` (int 1..12 | null)
  - `is_retro` (bool)
  - `speed` (number, deg/day)
  - `is_stationary` (bool)
  - `dispositor` (string | null)
- `houses` (array of objects):
  - `house` (int)
  - `sign` (string)
  - `degree` (number)
  - `abs_pos` (number)
  - `ruler` (string | null)
- `aspects` (array): элементы аспекта (структура может определяться в `calculate_natal_aspects`), типично:
  - `planet1` (string), `planet2` (string), `aspect` (string), `orb` (number)
- Аналитические блоки:
  - `jones_pattern` (object)
  - `dominants` (object)
  - `aspect_patterns` (object)
  - `planet_status` (object)
  - `compensatory` (object)
  - `balance` (object: `elements`, `qualities`)

Дополнительно: `POST /natal_svg` возвращает объект `{ "status": "success", "svg": "<svg>...</svg>" }`.

2) `POST /predict/daily`

Вход (`DailyPredictionRequest`):
- `date`, `time`, `tz`, `lat`, `lon` — те же типы
- `target_date` (string, required) — дата транзита

Выход (от `KerykeionEngine.transits`):
- `meta` (object): `{ type: "transits", date: "YYYY-MM-DD", target: <name> }`
- `moon_sign` (string)
- `transit_planets` (array): как в `planets`, дополнительно `in_natal_house` (int)
- `transits` (object): категории `daily`, `short_term`, `long_term`, `points`, каждая — массив объектов:
  - `transit_planet` (string)
  - `natal_planet` (string)
  - `aspect` (string)
  - `orb` (number)
  - `state` (string: `exact`, `applying`, `separating`, `retrograde_applying`, `retrograde_separating`, `unknown`)

3) `POST /predict/ephemeris`

Вход (`EphemerisEngineRequest`):
- `name` (string)
- `date`, `time`, `tz`, `lat`, `lon`
- `start_date` (string)
- `end_date` (string)
- `step_days` (int, default 5)

Выход:
- `meta` (object): `{ type: "ephemeris", start, end, step }`
- `natal_planets` (array of `{ name, abs_pos }`)
- `ephemeris` (array): элементы вида `{ date: "YYYY-MM-DD", "Sun": float, "Moon": float, ... }` — абсолютные градусы

4) `POST /synastry`

Вход (`SynastryRequest`): `{ person1: NatalChartRequest, person2: NatalChartRequest }`

Выход (от `KerykeionEngine.synastry`):
- `meta` (object)
- `aspects` (array): сырые синатрические аспекты
- `overlays` (object): `owner_planets_in_partner_houses`, `partner_planets_in_owner_houses` — массивы наложений

5) `POST /horary`

Вход (`HoraryRequest`): `lat`, `lon`, `question`, `dt_utc` (UTC datetime string)

Выход: структура похожа на `natal`, с `meta.type = "horary"` и `meta.question`.

6) `POST /solar`

Вход (`SolarReturnRequest`):
- `user_data` (NatalChartRequest), `year` (int), `return_lat`, `return_lon`, `return_tz` (опционально)

Выход: уменьшенно та же структура, что и `natal`, с `meta.type = "solar_return"`, `meta.solar_year`, `meta.location_name`.

Примечания по nullable/опциональным полям
- `house` может быть `null` в редких фолбэк-сценариях.
- Аналитические блоки (`dominants`, `jones_pattern` и т.д.) могут содержать пустые словари или отсутствовать полностью, в зависимости от реализации анализаторов.

Файл с моделями входа: `app/schemas.py`.


