# Примеры запросов (curl)

Замените `<INTERNAL_API_KEY>` на ваш ключ.

Пример — /natal

```bash
curl -s -X POST http://localhost:8000/natal \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <INTERNAL_API_KEY>" \
  -d '{
    "date": "1987-05-15",
    "time": "13:45:00",
    "tz": "+03:00",
    "lat": 59.9311,
    "lon": 30.3609
  }'
```

Пример — /natal_web (с дополнительными полями)

```bash
curl -s -X POST http://localhost:8000/natal_web \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <INTERNAL_API_KEY>" \
  -d '{
    "name": "Ivan",
    "date": "1987-05-15",
    "time": "13:45:00",
    "tz": "+03:00",
    "lat": 59.9311,
    "lon": 30.3609,
    "house_system": "P",
    "node_type": "true"
  }'
```

Пример — /natal_svg

```bash
curl -s -X POST http://localhost:8000/natal_svg \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <INTERNAL_API_KEY>" \
  -d '{
    "name": "Ivan",
    "date": "1987-05-15",
    "time": "13:45:00",
    "tz": "+03:00",
    "lat": 59.9311,
    "lon": 30.3609,
    "house_system": "P"
  }'
```

Пример — /predict/daily

```bash
curl -s -X POST http://localhost:8000/predict/daily \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <INTERNAL_API_KEY>" \
  -d '{
    "date": "1987-05-15",
    "time": "13:45:00",
    "tz": "+03:00",
    "lat": 59.9311,
    "lon": 30.3609,
    "target_date": "2026-04-11"
  }'
```

Пример — /predict/ephemeris

```bash
curl -s -X POST http://localhost:8000/predict/ephemeris \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <INTERNAL_API_KEY>" \
  -d '{
    "name": "User",
    "date": "1987-05-15",
    "time": "13:45:00",
    "tz": "+03:00",
    "lat": 59.9311,
    "lon": 30.3609,
    "start_date": "2026-04-01",
    "end_date": "2026-04-30",
    "step_days": 5
  }'
```

Postman
- Вы можете создать коллекцию, импортировав эти curl-запросы или JSON, приведённый выше.

Примечание
- Некоторые ответы содержат большие структуры и/или SVG; для просмотра SVG используйте браузер или сохраните ответ в файл.

## Примеры ответов (статические сниппеты)

Ниже — упрощённые, но реалистичные примеры полной JSON-ответной структуры для основных endpoint'ов.

### Пример ответа — `natal` (натальная карта)

```json
{
  "meta": {
    "engine": "kerykeion_v5",
    "subject": "User",
    "datetime": "1987-05-15T13:45:00",
    "location": {"lat": 59.9311, "lon": 30.3609},
    "chart_ruler": "Mercury"
  },
  "planets": [
    {"name": "Sun", "sign": "Ta", "sign_id": 1, "degree": 24.1234, "abs_pos": 54.1234, "house": 10, "is_retro": false, "speed": 1.0234, "is_stationary": false, "dispositor": "Venus"},
    {"name": "Moon", "sign": "Ge", "sign_id": 2, "degree": 3.5678, "abs_pos": 63.5678, "house": 11, "is_retro": false, "speed": 13.174, "is_stationary": false, "dispositor": "Mercury"},
    {"name": "Mercury", "sign": "Ta", "sign_id": 1, "degree": 18.4321, "abs_pos": 48.4321, "house": 10, "is_retro": false, "speed": 1.045, "is_stationary": false, "dispositor": "Venus"}
  ],
  "houses": [
    {"house": 1, "sign": "Ar", "degree": 5.123, "abs_pos": 5.123, "ruler": "Mars"},
    {"house": 2, "sign": "Ta", "degree": 25.321, "abs_pos": 25.321, "ruler": "Venus"}
  ],
  "aspects": [
    {"planet1": "Sun", "planet2": "Moon", "aspect": "Trine", "orb": 0.56},
    {"planet1": "Sun", "planet2": "Mercury", "aspect": "Conjunction", "orb": 5.69}
  ],
  "jones_pattern": {"exists": false},
  "dominants": {"by_power": ["Sun", "Mercury"]},
  "aspect_patterns": {"yod": false},
  "planet_status": {},
  "compensatory": {},
  "balance": {"elements": {"fire": 2, "earth": 3, "air": 4, "water": 1}, "qualities": {"cardinal": 3, "fixed": 4, "mutable": 3}}
}
```

### Пример ответа — `transits` (транзиты для указанной даты)

```json
{
  "meta": {"type": "transits", "date": "2026-04-11", "target": "User"},
  "moon_sign": "Le",
  "transit_planets": [
    {"name": "Mars", "sign": "Pi", "abs_pos": 351.2345, "degree": 21.2345, "house": 6, "speed": -0.5, "is_retro": true, "in_natal_house": 5},
    {"name": "Moon", "sign": "Le", "abs_pos": 140.1234, "degree": 20.1234, "house": 8, "speed": 13.2, "is_retro": false, "in_natal_house": 8}
  ],
  "transits": {
    "daily": [
      {"transit_planet": "Moon", "natal_planet": "Sun", "aspect": "Opposition", "orb": 1.12, "state": "separating"}
    ],
    "short_term": [
      {"transit_planet": "Mars", "natal_planet": "Mercury", "aspect": "Square", "orb": 0.78, "state": "retrograde_applying"}
    ],
    "long_term": [],
    "points": []
  }
}
```

### Пример ответа — `ephemeris` (графическая эфемерида)

```json
{
  "meta": {"type": "ephemeris", "start": "2026-04-01", "end": "2026-04-11", "step": 5},
  "natal_planets": [
    {"name": "Sun", "abs_pos": 54.1234},
    {"name": "Moon", "abs_pos": 63.5678}
  ],
  "ephemeris": [
    {"date": "2026-04-01", "Sun": 10.1234, "Moon": 120.5678, "Mars": 200.2345},
    {"date": "2026-04-06", "Sun": 15.2345, "Moon": 145.6789, "Mars": 205.3456},
    {"date": "2026-04-11", "Sun": 20.3456, "Moon": 170.7890, "Mars": 210.4567}
  ]
}
```

Примечание: это статические примеры для документации — реальные ответы содержат больше полей и могут отличаться по деталям и формату полей аналитики.

## GEO — Примеры запросов и статические ответы

Ниже приведены примеры curl-запросов к `geo` маршрутам и упрощённые примерные ответы.

### Пример — /geo/astrocartography (только линии ACG)

```bash
curl -s -X POST http://localhost:8000/geo/astrocartography \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <INTERNAL_API_KEY>" \
  -d '{
    "date": "1987-05-15",
    "time": "13:45:00",
    "tz": "+03:00",
    "lat": 59.9311,
    "lon": 30.3609
  }'
```

Пример ответа (фрагмент):

```json
{
  "status": "success",
  "data": {
    "Sun": {
      "MC": [[[45.0, 23.456], [40.0, 23.456]]],
      "IC": [[[45.0, -156.544], [40.0, -156.544]]],
      "ASC": [[[45.0, 10.123], [30.0, 12.345]]],
      "DSC": [[[45.0, -169.877], [30.0, -167.655]]],
      "Zenith": [12.345, 23.456]
    }
  }
}
```

### Пример — /geo/local-space (линии Local Space)

```bash
curl -s -X POST http://localhost:8000/geo/local-space \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <INTERNAL_API_KEY>" \
  -d '{
    "date": "1987-05-15",
    "time": "13:45:00",
    "tz": "+03:00",
    "lat": 59.9311,
    "lon": 30.3609
  }'
```

Пример ответа (фрагмент):

```json
{
  "status": "success",
  "ls_data": {
    "Sun": {"azimuth": 120.1234, "forward_paths": [[[59.93,30.36],[60.1,30.5]]], "reverse_paths": [[[59.93,30.36],[59.7,30.2]]]},
    "Moon": {"azimuth": 45.9876, "forward_paths": [[[59.93,30.36],[62.0,32.0]]], "reverse_paths": [[[59.93,30.36],[57.0,28.0]]]}
  }
}
```

### Пример — /geo/astrocartography-full (полная карта + города)

```bash
curl -s -X POST http://localhost:8000/geo/astrocartography-full \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <INTERNAL_API_KEY>" \
  -d '{
    "date": "1987-05-15",
    "time": "13:45:00",
    "tz": "+03:00",
    "lat": 59.9311,
    "lon": 30.3609
  }'
```

Пример ответа (сокращённо):

```json
{
  "status": "success",
  "lines": { /* ACG lines */ },
  "ls_data": { /* Local Space */ },
  "cities": [
    {"name": "Helsinki", "lat": 60.1699, "lon": 24.9384, "aspects": [{"planet":"Sun","angle":"MC","distance_km":120,"score":80}], "is_crossing": false}
  ]
}
```

### Пример — /geo/evaluate_city (сырые данные релокации)

```bash
curl -s -X POST http://localhost:8000/geo/evaluate_city \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <INTERNAL_API_KEY>" \
  -d '{
    "date": "1987-05-15",
    "time": "13:45:00",
    "tz": "+03:00",
    "lat": 59.9311,
    "lon": 30.3609,
    "target_lat": 56.8389,
    "target_lon": 60.6057,
    "city_name": "Yekaterinburg"
  }'
```

Пример ответа:

```json
{
  "status": "success",
  "data": {
    "city": "Yekaterinburg",
    "coordinates": {"lat": 56.8389, "lon": 60.6057},
    "angles": {"Ascendant": 123.4567, "MC": 210.9876},
    "cusps": [123.4567, 154.3210, ...],
    "planets_in_houses": {"Sun": {"absolute_degree": 54.1234, "new_house": 10}, "Moon": {"absolute_degree": 63.5678, "new_house": 11}}
  }
}
```

### Пример — /geo/check_point (точечная проверка)

```bash
curl -s -X POST http://localhost:8000/geo/check_point \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <INTERNAL_API_KEY>" \
  -d '{
    "date": "1987-05-15",
    "time": "13:45:00",
    "tz": "+03:00",
    "lat": 59.9311,
    "lon": 30.3609,
    "target_lat": 55.7558,
    "target_lon": 37.6176,
    "target_name": "Moscow"
  }'
```

Пример ответа:

```json
{
  "status": "success",
  "data": {
    "name": "Moscow",
    "lat": 55.7558,
    "lon": 37.6176,
    "aspects": [{"planet":"Moon","angle":"ASC","distance_km":45,"score":92}],
    "is_crossing": true
  }
}
```

### Пример — /geo/local-space-chart

```bash
curl -s -X POST http://localhost:8000/geo/local-space-chart \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <INTERNAL_API_KEY>" \
  -d '{
    "date": "1987-05-15",
    "time": "13:45:00",
    "tz": "+03:00",
    "lat": 59.9311,
    "lon": 30.3609
  }'
```

Пример ответа (фрагмент):

```json
{
  "status": "success",
  "data": {
    "meta": {"type": "local_space_chart", "lat": 59.9311, "lon": 30.3609},
    "planets": [{"name":"Sun","azimuth":120.1234,"altitude":10.2345,"is_above_horizon":true}],
    "aspects": [{"p1":"Sun","p2":"Moon","type":"opposition","orb":1.234}]
  }
}
```

Примечание: ответы приведены в упрощённом виде; реальные ответы содержат более подробные массивы точек для отрисовки линий и дополнительные поля.
