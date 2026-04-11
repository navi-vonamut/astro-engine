# Сопоставление API эндпоинтов с методами `KerykeionEngine`

Цель: быстрое соответствие, где в коде находится реализация логики, вызываемой по API.

- `POST /natal` -> `KerykeionEngine.natal(inp: BirthInput)`
  - Файл: `app/routes/natal.py` вызывает `KerykeionEngine().natal`
  - Основная реализация: `app/engine/kerykeion_engine.py` -> `natal`

- `POST /natal_web` -> `KerykeionEngine.natal(inp)` (тот же метод, разные поля входа)

- `POST /natal_svg` -> `KerykeionEngine.get_natal_svg(inp)`
  - Генерация SVG: `app/engine/render/svg_builder.py` (`build_natal_svg`)

- `POST /predict/daily` -> `KerykeionEngine.transits(natal_inp, target_date)`
  - Код в `app/routes/predict.py` создает `BirthInput` и вызывает `transits`.
  - Реализация транзитов: `app/engine/kerykeion_engine.py` -> `transits`

- `POST /predict/ephemeris` -> `KerykeionEngine.graphical_ephemeris(natal_inp, start_date, end_date, step_days)`
  - Реализация: `kerykeion_engine.graphical_ephemeris`

- `POST /synastry` -> `KerykeionEngine.synastry(p1, p2)`
  - Реализация: `kerykeion_engine.synastry`
  - Вспомогательные калькуляторы: `app/engine/calculators/synastry_calc.py`

- `POST /horary` -> `KerykeionEngine.horary(inp, question)`
  - Реализация: `kerykeion_engine.horary`

- `POST /solar` -> `KerykeionEngine.solar_return(natal_inp, year, loc_lat, loc_lon, loc_tz)`
  - Вычисление входных данных для соляра: `app/engine/calculators/solar_calc.py` (`calculate_solar_return_input`)

Где смотреть модели и утилиты
- Модели входа: `app/engine/core/models.py`
- Утилиты по дате/временной зоне: `app/engine/core/utils.py`
- Константы (списки точек и домов): `app/engine/core/constants.py`
- SWISSEPH-фолбеки и скорость: в `kerykeion_engine._extract_planet` и `_get_swisseph_speed`

Короткий чек-лист для разработчика
- Если нужно добавить новый эндпоинт — реализуйте роут в `app/routes/*` и вызовите соответствующий метод движка.
- Для изменения формата ответа — правьте в `kerykeion_engine` или в соответствующих анализаторах в `app/engine/analyzers`.

