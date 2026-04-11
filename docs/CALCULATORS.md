# Документация: `app/engine/calculators`

В этой секции описаны вспомогательные калькуляторы, используемые движком: расчёт аспектов, синатрия и подготовка данных для соляра.

Файлы:
- `app/engine/calculators/aspects_calc.py` — расчёт натальных аспектов и параллелей.
- `app/engine/calculators/synastry_calc.py` — синатрические аспекты и наложения домов.
- `app/engine/calculators/solar_calc.py` — поиск точного момента соляра и подготовка `BirthInput`.

---

## aspects_calc.py

Функция: `calculate_natal_aspects(planets_list: List[Dict[str, Any]], julian_day: float) -> List[Dict[str, Any]]`

Описание:
- Вычисляет аспекты (долготные) и параллели по склонению между всеми парами точек в `planets_list`.
- Добавляет в каждый объект планеты поля `lat` (широта) и `decl` (склонение), беря их через swisseph.

Алгоритм:
1. Для каждой планеты из `planets_list`, если она присутствует в `SWISSEPH_OBJECTS`, получает её гео-координаты через `swe.calc_ut` и `swe.FLG_EQUATORIAL`.
2. Перебирает уникальные пары планет и игнорирует очевидные пары осей (Ascendant/Descendant, IC/MC, Node-пары).
3. Вычисляет разницу долгот `diff` (минимальная разница через круг) и для каждого аспекта из `ASPECT_RULES` проверяет орб.
   - Для специальных строго определённых точек (из `STRICT_POINTS`) используется более жёсткий орб.
4. Вычисляет параллели по склонению (`decl`) с порогом 1.2°.

Возвращаемое значение:
- Список объектов аспекта: `{ "p1": <name>, "p2": <name>, "type": <aspect_name>, "orb": <float>, "is_applying": False }`.

Параметры и константы:
- `ASPECT_RULES` (в `app/engine/core/constants.py`) содержит набор углов с обычным и строгим орбом.
- `STRICT_POINTS` — набор фиктивных точек, для которых орбы строже.

Ошибки и граничные случаи:
- Если swisseph бросает исключение при получении координат — растение деградирует и ставит `lat`/`decl` в `0.0`.

---

## synastry_calc.py

Функция: `get_synastry_aspects(subject1, subject2) -> List[Dict[str, Any]]`

Описание:
- Использует `kerykeion.AspectsFactory.dual_chart_aspects` для получения списка аспектов между двумя объектами `subject`.
- Фильтрует по белому списку планет и по набору разрешённых типов аспектов.
- Применяет "умные орбисы" для синастрии: большие орбы для Луны и Солнца, маленькие для узлов и астероидов.

Возвращаемое значение:
- Список аспектов `{ "person1_object": <str>, "aspect": <str>, "person2_object": <str>, "orb": <float> }`.

Функция: `calculate_house_overlays(planets: List[Dict], partner_houses: List[Dict]) -> List[Dict]`

Описание:
- Для каждого планетного объекта из `planets` вычисляет, в какой дом партнера он попадает с помощью `get_house_for_degree`.
- Возвращает список `{ "planet": <name>, "in_partner_house": <int>, "partner_house_sign": <str> }`.

Граничные случаи:
- Если индекс дома выходит за рамки массива домов — возвращает пустую строку для `partner_house_sign`.

---

## solar_calc.py

Функции:
- `get_utc_jd(inp: BirthInput) -> float` — конвертирует локальные дату/время и `tz` в Julian Day (UTC).
- `find_exact_solar_return_jd(natal_jd_utc: float, year: int) -> float` — находит JD момента, когда транзитное Солнце возвращается в ту же долготную позицию, что и в натале.
- `calculate_solar_return_input(natal_inp: BirthInput, year: int, loc_lat: float, loc_lon: float, loc_tz: str) -> BirthInput` — объединяет оба шага и возвращает новый `BirthInput` для построения карты Соляра.

Алгоритм `find_exact_solar_return_jd` (кратко):
1. Берёт натальную долготу Солнца через `swe.calc_ut`.
2. Инициализирует JD на полдень дня рождения в целевом году.
3. Итеративно обновляет `jd_iter` по правилу `jd_iter += delta / sun_speed`, где `delta` — разница долгот (корректированная по кругу), `sun_speed` — скорость Солнца (deg/day).
4. Останавливается, когда `abs(delta)` становится очень маленьким.

Алгоритм `calculate_solar_return_input`:
1. Конвертирует `natal_inp` в natal_jd_utc.
2. Находит solar_jd_utc через `find_exact_solar_return_jd`.
3. Конвертирует JD в локальную дату/время целевой локации, учитывая `loc_tz`.
4. Формирует и возвращает `BirthInput` для дальнейшего использования в движке.

Точность и ограничения
- `find_exact_solar_return_jd` использует итерационный метод с допущением, что скорость Солнца ненулевая и изменения непрерывны; обычно сходится быстро за несколько итераций.
- Обработка `tz` в `get_utc_jd` и `calculate_solar_return_input` основана на простом парсинге строки `+HH:MM` или `+HH` и не учитывает правила DST; для строгой точности лучше использовать `pytz` или `zoneinfo`.

---

### Рекомендации и следующие шаги
- Добавить в документацию небольшие блоки с примерами входов/выходов (JSON) для каждого калькулятора (например, пример `planets_list` для `calculate_natal_aspects`).
- Рассмотреть добавление unit-тестов для ключевых функций (аспекты, соляр), чтобы зафиксировать поведение при граничных случаях.

Сохранено в `docs/CALCULATORS.md`.
