# Документация: GeoAstroEngine

Этот документ описывает функциональность `GeoAstroEngine` в `app/engine/geo_engine.py`: что делает каждая функция, какие входы/выходы, используемые алгоритмы и практические примеры ответов.

Файлы реализации
- Основной движок: `app/engine/geo_engine.py`
- Гео-утилиты: `app/engine/core/geo_math.py`
- Маршруты API: `app/routes/geo.py`
- Список городов: `app/geo/data/major_cities.json` (загрузка — через `app/geo/cities.py`)

Зависимости
- `swisseph` (swisseph/swe) — вычисления астрономических координат и домов
- `numpy` — быстрые векторизованные расчёты расстояний
- `kerykeion` — для надёжного получения `julian_day` и subject в некоторых методах

Общие соглашения
- Все методы принимают `BirthInput` (см. `app/engine/core/models.py`) или производные параметры (lat/lon/city_name).
- Все долготы в выходах нормализованы функцией `normalize_lon` в `geo_math.py`.

Основные методы

1) get_astrocartography_lines(inp: BirthInput) -> Dict[str, Any]
- Описание: строит линии астрокартографии (MC/IC/ASC/DSC и Zenith) для набора точек (планет/астероидов) на глобальную карту.
- Алгоритм (кратко):
  - Берёт UTC Julian Day для входных данных (`get_utc_jd_from_input`).
  - Для каждой точки из `SWISSEPH_OBJECTS` получает прямое космическое положение (RA/decl) через `swe.calc_ut`.
  - Рассчитывает долготы линий MC/IC/ASC/DSC с учётом GST (sidereal time): `lon_mc = normalize_lon(ra - gst_deg)` и т. п.
  - Для ASC/DSC строит сегменты по широтам с обработкой пересечения линии перемены дат (`interpolate_dateline`).
- Вход: `BirthInput`.
- Выход: Словарь по точкам: для каждой точки `{ "MC": [[...]], "IC": [[...]], "ASC": [[segments...]], "DSC": [[segments...]], "Zenith": [decl, lon] }`.
- Ограничения: используется проекция Меркатора с максимальной широтой `MAX_MERCATOR_LAT = 85°`.

2) get_local_space_lines(inp: BirthInput) -> Dict[str, Any]
- Описание: строит для наблюдателя локальные азимутальные линии (Local Space rays) для углов карты и планет.
- Алгоритм (кратко):
  - Устанавливает топоцентрические координаты наблюдателя (`swe.set_topo`).
  - Для углов (Ascendant, MC) и для каждой планеты получает азимут через `swe.azalt` и переводит азимут в компасную систему (0° = Север).
  - Генерирует геодезический путь в направлении азимута через `generate_geodesic_path` (в `geo_math.py`).
- Вход: `BirthInput`.
- Выход: Словарь: для каждой точки `{ "azimuth": float, "forward_paths": [...], "reverse_paths": [...] }`.

3) calculate_city_scores_combined(acg_data, ls_data, cities, birth_lat, birth_lon) -> List[dict]
- Описание: объединяет линии ACG и Local Space с набором городов и вычисляет скор для каждого города по близости линий.
- Алгоритм (кратко):
  - Содержащиеся в `acg_data` точки агрегируются в массив координат (lat, lon).
  - Векторизованно вычисляются большие матрицы расстояний (хаверсин) от городов до всех точек линий (numpy) и выбираются те, что внутри `MAX_ORB_KM` (700 km).
  - Для каждой такой близости даётся оценка `score` (максимум 150 для Zenith, 100 для обычных линий), пропорционально уменьшению расстояния.
  - Local Space добавляет небольшие бонусы (в пределах LS_ORB_DEGREES = 3°) на основе азимута.
  - Возвращается список городов с полем `aspects` (список найденных совпадений) и `is_crossing` (есть ли совпадение и в ACG и в LS).
- Вход: `acg_data` — результат `get_astrocartography_lines`, `ls_data` — результат `get_local_space_lines`, `cities` — список {name, lat, lon,...}, `birth_lat`, `birth_lon` — координаты центра.
- Выход: список городов с доп. полями `aspects`, `is_crossing`.

4) get_relocation_raw_data(inp: BirthInput, target_lat: float, target_lon: float, city_name: str) -> Dict[str, Any]
- Описание: даёт «сырые» данные релокации для заданных координат — новые куспы домов, углы и какие планеты попадают в какие дома.
- Алгоритм (кратко):
  - Вычисляет дома на целевой локализации через `swe.houses_ex`.
  - Для каждой точки `SWISSEPH_OBJECTS` получает абсолютную долготу через `swe.calc_ut` и находит, в какой дом попадает (учёт цикличности домов).
- Выход: объект с `city`, `coordinates`, `angles` (Ascendant/MC), `cusps` (массив 12), `planets_in_houses` (карта имени→{ absolute_degree, new_house }).

5) check_single_point(inp: BirthInput, target_lat: float, target_lon: float, target_name: str) -> Dict[str, Any]
- Описание: быстрый чек одной точки (например, при клике по карте) — совмещает ACG + LS и выдаёт оценки для конкретной точки.
- Алгоритм: вызывает `get_astrocartography_lines`, `get_local_space_lines` и затем `calculate_city_scores_combined` для одного города.
- Выход: либо объект города с `aspects`, либо шаблон с пустым `aspects`.

6) check_local_space_point(inp: BirthInput, target_lat: float, target_lon: float, target_name: str) -> Dict[str, Any]
- Описание: проверка только Local Space для точки — возвращает azimuth/bearing и найденные локальные аспекты (в пределах 3°).
- Выход: { name, center_lat, center_lon, lat, lon, bearing, aspects, is_crossing }

7) get_local_space_chart(inp) -> Dict[str, Any]
- Описание: строит круговую Local Space карту: азимуты планет, высоты и локальные аспекты между ними.
- Алгоритм:
  - Получаем JD через `kerykeion.AstrologicalSubjectFactory.from_birth_data`.
  - Для фиксированного набора точек (`Sun..Pluto, Chiron, True_North_Lunar_Node, Mean_Lilith`) вычисляем азимут и высоту через `swe.azalt`.
  - Затем для пар планет ищем локальные аспекты по азимутам с жёсткими орбами (0°±3°, 60°±2°, 90°±2.5°, 120°±2°, 180°±3°).
- Выход: объект с `meta`, `planets` (list of {name, azimuth, altitude, is_above_horizon}) и `aspects`.

Примеры ответов (сокращённые)

Пример `POST /geo/astrocartography` -> `get_astrocartography_lines` (фрагмент):
```json
{
  "status": "success",
  "data": {
    "Sun": {
      "MC": [[[45.0, 23.456]]],
      "IC": [[[45.0, -156.544]]],
      "ASC": [[[...segments...]]],
      "DSC": [[[...segments...]]],
      "Zenith": [12.345, 23.456]
    },
    "Moon": { ... }
  }
}
```

Пример `POST /geo/local-space-chart` -> `get_local_space_chart`:
```json
{
  "status": "success",
  "data": {
    "meta": {"type": "local_space_chart", "lat": 59.93, "lon": 30.36},
    "planets": [ {"name":"Sun","azimuth":120.1234,"altitude":10.2345,"is_above_horizon":true}, ...],
    "aspects": [ {"p1":"Sun","p2":"Moon","type":"opposition","orb":1.234} ]
  }
}
```

Производительность и рекомендации
- `calculate_city_scores_combined` использует векторные numpy-операции и рассчитан на работу с несколькими тысячами городов; тем не менее вызов `get_astrocartography_lines` и `get_local_space_lines` включает циклы и вызовы `swe.calc_ut` — эти части тяжёлые. Кеширование `acg_data` и `ls_data` для одного натала рекомендуется при массовой оценке городов.
- Параллелизация: можно распараллелить обработку наборов городов по чанкам при выборе большого `cities` списка.

Ошибки и граничные случаи
- Вызовы к swisseph могут бросать исключения; код пытается обработать их и продолжить сбор данных (игнорирует недоступные точки).
- При пересечении линии перемены дат используется `interpolate_dateline` для аккуратного разделения сегмента линий.
- `get_relocation_raw_data` использует `swe.houses_ex` с попыткой системы `P`, а затем `W` как fallback.

Ссылки для разработчика
- Просмотрите реализацию: `app/engine/geo_engine.py` (весь файл)
- Гео-утилиты: `app/engine/core/geo_math.py`
- Роуты: `app/routes/geo.py`
- Города: `app/geo/cities.py` и `app/geo/data/major_cities.json`

