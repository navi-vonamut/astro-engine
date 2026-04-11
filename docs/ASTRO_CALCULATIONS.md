# Астрологические расчёты — подробная документация

Этот документ описывает, как устроены и какие алгоритмы используются в сервисе для расчётов натальных карт, транзитов, соляров и графических эфемерид.

**К чему относится**
- Реализация движка: [app/engine/kerykeion_engine.py](app/engine/kerykeion_engine.py)
- Модель входных данных: [app/engine/core/models.py](app/engine/core/models.py)
- Вспомогательные калькуляторы и анализаторы (аспекты, джонс, домовые наложения и т.д.) находятся в `app/engine/calculators` и `app/engine/analyzers`.

**Ключевые понятия и единицы**
- `abs_pos` — абсолютный градус положения точки на эклиптике в диапазоне $[0,360)$, отсчёт от 0° Овна.
- `degree` — градус внутри знака: $degree = abs\_pos \bmod 30$ (значения $[0,30)$).
- `sign_id` — целая часть $\lfloor abs\_pos/30 \rfloor$ (0..11), где 0 = Овен.
- `house` — номер дома 1..12. Если вычисления дома отсутствуют, используется утилита `get_house_for_degree`.
- `is_retro` — вычисляется как `speed < 0` (реальная скорость берётся из swisseph при наличии).
- `is_stationary` — проверка `abs(speed) < 0.05` (в коде это критерий стационарности).

**Входной объект**
- Формат данных: см. модель `BirthInput` в [app/engine/core/models.py](app/engine/core/models.py).
- Обязательные поля: `date` (YYYY-MM-DD), `time` (HH:MM:SS), `tz` (например "+03:00" или "Europe/Warsaw"), `lat`, `lon`.
- Опциональные: `name`, `house_system` (по умолчанию `P`), `node_type` (`true` или `mean`, по умолчанию `true`).

**Главные методы движка (соответствие API)**
- `natal(inp: BirthInput) -> Dict` — строит полную натальную карту (планеты, дома, аспекты, доминанты и т.д.). См. реализацию: [app/engine/kerykeion_engine.py](app/engine/kerykeion_engine.py).
- `get_natal_svg(inp)` — генерирует SVG через `build_natal_svg`.
- `transits(natal_inp, transit_date)` — строит транзитную карту на `transit_date`, сравнивает её с наталом и возвращает категоризированный список аспектов и транзитных планет.
- `graphical_ephemeris(natal_inp, start_date, end_date, step_days)` — возвращает табличную эфемериду (abs_pos для набора точек) с шагом `step_days`.
- `solar_return(natal_inp, year, loc_lat, loc_lon, loc_tz)` — расчёт соляра, опирается на `calculate_solar_return_input`.

**Как извлекаются позиционные данные**
- Основная работа идёт через `AstrologicalSubjectFactory` и `ChartDataFactory` из пакета `kerykeion` (см. `build_subject` и `ChartDataFactory.create_natal_chart_data`).
- Для каждой точки движок использует `_extract_planet`: сначала пробует взять значение из `subject` (kerykeion), если нет — падает на прямой вызов `swisseph` (фолбек).
- Скорости планет (и ретроградность) берутся через swisseph: `swe.calc_ut(..., FLG_SPEED)`.

**Фиктивные точки и специальные вычисления**
- Южный узел: вычисляется как `sn_abs_pos = (north_node["abs_pos"] + 180) % 360` и добавляется в список точек.
- Vertex и Fortune вычисляются через `swe.houses(...)` и формулы в коде (см. блок в `natal`).

**Аспекты и их состояние**
- Основные аспекты, используемые в транзитах: Conjunction (0°), Sextile (60°), Square (90°), Trine (120°), Opposition (180°). (Словарь `ASPECT_ANGLES` в коде.)
- Орб: при вычислении используется абсолютная разность по кругу. Формула орба:

$$\text{orb} = \min(|\theta_1-\theta_2|,\,360-|\theta_1-\theta_2|)$$

- Состояние аспекта определяется функцией `_get_aspect_state`:
  - Берётся текущая орба `current_orb` и орба через небольшой шаг времени `next_orb` (транзитная планета сдвигается на $0.1$ дня: $next\_pos = t\_pos + t\_speed \times 0.1$).
  - Если `current_orb < 0.1` → состояние `exact`.
  - Если `next_orb < current_orb` → состояние `applying` (или `retrograde_applying` если скорость отрицательная).
  - Иначе → `separating` (или `retrograde_separating`).
- Комбустность: метод `_is_combust(planet_abs_pos, sun_abs_pos)` возвращает `True` если орб до Солнца меньше $8.5^\circ$ (учтён круговой расчёт разности).

**Категоризация транзитов**
- Транзитные аспекты разделены по категориям в `transits`: `daily` (Moon), `short_term` (Sun, Mercury, Venus, Mars), `long_term` (Jupiter, Saturn, Uranus, Neptune, Pluto), `points` (узлы, астероиды, Vertex, Fortune и т.д.).

**Формат выходных данных**
- Натал:
  - `meta` — метаинформация (`engine`, `subject`, `datetime`, `location`, `chart_ruler`).
  - `planets` — список объектов планет/точек. Пример элемента:

```json
{
  "name": "Sun",
  "sign": "Ar",
  "sign_id": 0,
  "degree": 15.1234,
  "abs_pos": 15.1234,
  "house": 10,
  "is_retro": false,
  "speed": 1.0234,
  "is_stationary": false,
  "dispositor": "Mercury"
}
```

  - `houses` — список домов с `house`, `sign`, `degree`, `abs_pos`, `ruler`.
  - `aspects` — чистые натальные аспекты (см. `calculate_natal_aspects`).
  - `jones_pattern`, `dominants`, `aspect_patterns`, `planet_status`, `compensatory`, `balance` — аналитические блоки, возвращаемые соответствующими анализаторами.

- Транзиты (структура из `transits` метода):
  - `meta`: `{ type: "transits", date: "YYYY-MM-DD", target: <name> }`
  - `transit_planets`: список транзитных планет с `in_natal_house` и базовыми полями как в `planets`.
  - `transits`: объект с категориями `daily`, `short_term`, `long_term`, `points` — каждая запись:

```json
{
  "transit_planet": "Mars",
  "natal_planet": "Sun",
  "aspect": "Square",
  "orb": 1.23,
  "state": "applying"
}
```

- Эфемериды (`graphical_ephemeris`):
  - `meta`: параметры запроса
  - `natal_planets`: позиции натала (abs_pos)
  - `ephemeris`: массив дат с полями `date` и абсолютными позициями точек в формате `{ "date": "YYYY-MM-DD", "Sun": 123.4567, "Moon": ... }`.

**Точность и пограничные случаи**
- Для скорости и точных положений используется swisseph. Если `kerykeion` не вернёт значение для точки — код делает фолбек на swisseph (`swe.calc_ut`).
- При вычислениях домов используется `swe.houses(...)` и также `get_house_for_degree` для соответствия градус→дом.
- Ограничения: метод `transits` строит транзитную карту на 12:00 локального времени — это выбор, достаточный для дневных сводок, но не для минутной точности при быстрых аспектах.

**Ссылки в коде**
- Основной движок: [app/engine/kerykeion_engine.py](app/engine/kerykeion_engine.py)
- Модели: [app/engine/core/models.py](app/engine/core/models.py)
- Утилиты (нормализация дат, tz): [app/engine/core/utils.py](app/engine/core/utils.py)
- Калькуляторы аспектов: [app/engine/calculators/aspects_calc.py](app/engine/calculators/aspects_calc.py)



