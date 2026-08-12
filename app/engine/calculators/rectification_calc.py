"""
Универсальный движок авторектификации — Strict Aspect & Ruler Matrix.

Ключевые принципы:
  1. Только жёсткие аспекты (0°, 90°, 180°) для переменных углов карты.
     Мягкие аспекты (трин, секстиль) не могут надёжно зафиксировать событие.
  2. Каждый тип события привязан к строго определённым домам/планетам.
     Ненужные планеты не участвуют → шум снижается кратно.
  3. Штраф за шум: если у кандидата нет ни одного «ключевого» аспекта
     (управитель главного дома события к углам карты), его балл занижается.
  4. Динамические управители: куспиды пересчитываются для каждой минуты
     — критично для высоких широт и «иллюзии полудня».
"""
import swisseph as swe
import datetime
import pytz
from typing import Dict, List, Any, Optional, Tuple

from app.engine.core.models import BirthInput
from app.engine.calculators.directions_calc import calculate_direction_arc
from app.engine.core.utils import parse_ymd, tz_to_pytz
from app.engine.core.constants import SIGNS_SHORT


def lon_to_sign(lon: float) -> str:
    SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
    idx = int((lon % 360.0) // 30)
    deg = int((lon % 360.0) % 30)
    return f"{SIGNS[idx]} {deg}°"


# ─────────────────────────────────────────────────────────────────────────────
#  Управители знаков (классическая + современная система)
# ─────────────────────────────────────────────────────────────────────────────
SIGN_RULERS: Dict[str, str] = {
    "Aries": "Mars",       "Taurus": "Venus",      "Gemini": "Mercury",
    "Cancer": "Moon",      "Leo": "Sun",            "Virgo": "Mercury",
    "Libra": "Venus",      "Scorpio": "Pluto",      "Sagittarius": "Jupiter",
    "Capricorn": "Saturn", "Aquarius": "Uranus",    "Pisces": "Neptune",
    # Трёхбуквенные алиасы
    "Ari": "Mars",  "Tau": "Venus",  "Gem": "Mercury", "Can": "Moon",
    "Vir": "Mercury","Lib": "Venus", "Sco": "Pluto",   "Sag": "Jupiter",
    "Cap": "Saturn", "Aqu": "Uranus","Pis": "Neptune",
}

# ─────────────────────────────────────────────────────────────────────────────
#  Сбалансированная матрица аспектов
#
#  Теперь и для осей (ASC/MC), и для планет учитываются как напряжённые,
#  так и гармоничные аспекты, но с разным весом (кризисы vs гармония).
# ─────────────────────────────────────────────────────────────────────────────
ALL_ASPECTS: List[Dict[str, Any]] = [
    {"name": "Conjunction", "angle": 0.0,   "weight": 3.0},  # Соединение (мощный старт)
    {"name": "Opposition",  "angle": 180.0, "weight": 2.5},  # Оппозиция (кризис/кульминация)
    {"name": "Square",      "angle": 90.0,  "weight": 2.5},  # Квадрат (напряжение/событие)
    {"name": "Trine",       "angle": 120.0, "weight": 2.0},  # Трин (гармоничное событие: брак, роды)
    {"name": "Sextile",     "angle": 60.0,  "weight": 1.5},  # Секстиль (возможность/реализация)
]

# Только ASC и MC — персональные оси карты, чувствительные к времени рождения.
# DSC и IC — антиподы, не добавляют информации при проверке Hard-аспектов.
DIRECTED_ANGLES = ["Ascendant", "Medium_Coeli"]

# ─────────────────────────────────────────────────────────────────────────────
#  Строгая схема событий
#
#  Структура:
#    "event_type": {
#        "primary_houses": [N, ...]   — главные дома события,
#                                       управители которых ОБЯЗАТЕЛЬНЫ для ключевого аспекта
#        "secondary_houses": [N, ...] — вспомогательные дома
#        "universal": ["Planet", ...]  — универсальные маркеры (если управитель не найден)
#        "primary_weight": float       — вес первичных управителей
#        "secondary_weight": float     — вес вторичных управителей
#    }
# ─────────────────────────────────────────────────────────────────────────────
EVENT_MATRIX: Dict[str, Dict] = {
    "marriage": {
        "primary_houses":   [7],
        "secondary_houses": [1],
        "universal":        ["Venus", "Juno", "Neptune"],
        "primary_weight":   3.0,
        "secondary_weight": 1.5,
        "universal_weight": 1.2,
    },
    "childbirth": {
        "primary_houses":   [5],
        "secondary_houses": [4],
        "universal":        ["Moon", "Ceres"],
        "primary_weight":   3.0,
        "secondary_weight": 1.5,
        "universal_weight": 1.5,
    },
    "military_service": {
        "primary_houses":   [12],
        "secondary_houses": [6],
        "universal":        ["Saturn", "Mars"],
        "primary_weight":   3.0,
        "secondary_weight": 1.2,
        "universal_weight": 1.5,
    },
    "isolation": {
        "primary_houses":   [12],
        "secondary_houses": [8],
        "universal":        ["Saturn", "Pluto"],
        "primary_weight":   3.0,
        "secondary_weight": 1.2,
        "universal_weight": 1.5,
    },
    "hospital": {
        "primary_houses":   [12, 6],
        "secondary_houses": [8],
        "universal":        ["Saturn", "Chiron"],
        "primary_weight":   2.5,
        "secondary_weight": 1.2,
        "universal_weight": 1.2,
    },
    "career_peak": {
        "primary_houses":   [10],
        "secondary_houses": [2],
        "universal":        ["Sun", "Jupiter", "Saturn"],
        "primary_weight":   3.0,
        "secondary_weight": 1.2,
        "universal_weight": 1.2,
    },
    "relocation": {
        "primary_houses":   [4],
        "secondary_houses": [9],
        "universal":        ["Moon", "Uranus"],
        "primary_weight":   2.5,
        "secondary_weight": 1.5,
        "universal_weight": 1.0,
    },
    "loss": {
        "primary_houses":   [8],
        "secondary_houses": [12],
        "universal":        ["Saturn", "Pluto"],
        "primary_weight":   3.0,
        "secondary_weight": 1.2,
        "universal_weight": 1.5,
    },
    "divorce": {
        "primary_houses":   [7],
        "secondary_houses": [12],
        "universal":        ["Mars", "Uranus", "Saturn"],
        "primary_weight":   3.0,
        "secondary_weight": 1.0,
        "universal_weight": 1.2,
    },
    # Универсальный fallback
    "_default": {
        "primary_houses":   [1, 10],
        "secondary_houses": [],
        "universal":        ["Sun", "Moon"],
        "primary_weight":   2.0,
        "secondary_weight": 1.0,
        "universal_weight": 0.8,
    },
}

# Коэффициент штрафа за шум: если у кандидата нет ни одного ключевого аспекта
# (т.е. управитель первичного дома не задействован), балл умножается на NOISE_PENALTY.
NOISE_PENALTY: float = 0.25


# ─────────────────────────────────────────────────────────────────────────────
#  Вспомогательные функции
# ─────────────────────────────────────────────────────────────────────────────

def _time_to_minutes(t_str: str) -> int:
    try:
        h, m = map(int, t_str.split(":"))
        return h * 60 + m
    except Exception:
        return 0


def _check_aspect(pos_a: float, pos_b: float, aspects: List[Dict], max_orb: float) -> Optional[Tuple[Dict, float]]:
    """
    Проверяет, есть ли между двумя позициями хотя бы один аспект из списка.
    Возвращает (aspect_dict, orb) первого найденного совпадения или None.
    """
    diff = abs(pos_a - pos_b)
    if diff > 180.0:
        diff = 360.0 - diff
    for asp in aspects:
        orb = abs(diff - asp["angle"])
        if orb <= max_orb:
            return asp, orb
    return None


def build_strict_targets(
    event_type: str,
    minute_rulers: Dict[int, str],
    planet_map: Dict[str, float],
) -> Tuple[List[Dict], List[str]]:
    """
    Строит список целей (planet_name, natal_pos, weight, is_primary)
    строго по EVENT_MATRIX — только планеты, управляющие нужными домами
    + универсальные маркеры.

    Returns:
        targets: [{"name": str, "abs_pos": float, "weight": float, "is_primary": bool}]
        primary_planets: [planet_name] — имена первичных управителей для штрафной проверки
    """
    schema = EVENT_MATRIX.get(event_type, EVENT_MATRIX["_default"])
    targets: List[Dict] = []
    seen: Dict[str, float] = {}      # name → max weight
    primary_planets: List[str] = []

    def _add(name: Optional[str], weight: float, is_primary: bool):
        if not name or name not in planet_map:
            return
        if name not in seen or weight > seen[name]:
            seen[name] = weight
            if is_primary and name not in primary_planets:
                primary_planets.append(name)

    # Первичные дома — самый высокий вес, обязательны для ключевого аспекта
    for house_num in schema["primary_houses"]:
        ruler = minute_rulers.get(house_num)
        _add(ruler, schema["primary_weight"], is_primary=True)

    # Вторичные дома
    for house_num in schema["secondary_houses"]:
        ruler = minute_rulers.get(house_num)
        _add(ruler, schema["secondary_weight"], is_primary=False)

    # Универсальные маркеры
    for planet in schema["universal"]:
        _add(planet, schema["universal_weight"], is_primary=False)

    # Собираем финальный список
    for name, weight in seen.items():
        targets.append({
            "name":       name,
            "abs_pos":    planet_map[name],
            "weight":     weight,
            "is_primary": name in primary_planets,
        })

    return targets, primary_planets


# ─────────────────────────────────────────────────────────────────────────────
#  Генератор сетки домов (1440 минут или заданное окно)
# ─────────────────────────────────────────────────────────────────────────────

def generate_window_grids(natal_inp: BirthInput, start_min: int, end_min: int) -> List[Dict[str, Any]]:
    """
    Для каждой минуты окна [start_min, end_min] вычисляет:
    - ASC, MC, DSC, IC
    - динамических управителей всех 12 куспидов
    """
    y, m, d = parse_ymd(natal_inp.date)
    tz_str = tz_to_pytz(str(natal_inp.tz))
    local_tz = pytz.timezone(tz_str)

    h_sys = str(natal_inp.house_system or "P").upper()
    if h_sys == "E":
        h_sys = "A"
    house_sys_byte = h_sys.encode("ascii")

    end_min = min(1439, max(start_min, end_min))
    grid = []

    for minute in range(start_min, end_min + 1):
        hh = minute // 60
        mm = minute % 60

        local_dt = local_tz.localize(datetime.datetime(y, m, d, hh, mm, 0))
        utc_dt   = local_dt.astimezone(pytz.utc)

        jd = swe.julday(
            utc_dt.year, utc_dt.month, utc_dt.day,
            utc_dt.hour + utc_dt.minute / 60.0 + utc_dt.second / 3600.0,
        )

        try:
            cusps, ascmc = swe.houses(
                jd, float(natal_inp.lat), float(natal_inp.lon), house_sys_byte
            )
        except Exception:
            # Полярные широты с несовместимой системой домов → пропускаем минуту
            continue

        rulers: Dict[int, str] = {}
        for i, c_pos in enumerate(cusps[:12]):
            sign_id  = int(c_pos // 30) % 12
            sign_name = SIGNS_SHORT[sign_id]
            rulers[i + 1] = SIGN_RULERS.get(sign_name, "Sun")

        asc = ascmc[0]
        mc  = ascmc[1]
        grid.append({
            "time":         f"{hh:02d}:{mm:02d}",
            "Ascendant":    asc,
            "Medium_Coeli": mc,
            "Descendant":   (asc + 180.0) % 360.0,
            "Imum_Coeli":   (mc  + 180.0) % 360.0,
            "rulers":       rulers,
        })

    return grid


# ─────────────────────────────────────────────────────────────────────────────
#  Главная функция
# ─────────────────────────────────────────────────────────────────────────────

def calculate_rectification(
    natal_inp:     BirthInput,
    natal_planets: List[Dict[str, Any]],
    natal_houses:  List[Dict[str, Any]],   # совместимость с вызывающим кодом
    events:        List[Dict[str, Any]],
    ai_signatures: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    mode:          str   = "symbolic",
    max_orb:       float = 0.5,
    start_time:    str   = "00:00",
    end_time:      str   = "23:59",
) -> Dict[str, Any]:
    """
    Строгий матричный скорринг.

    Для каждой минуты суток:
      1. Строим список целей по EVENT_MATRIX (первичные + вторичные управители + маркеры).
      2. Вектор A: Dir(ASC|MC) → Hard-аспект → Nat(цель) — максимальный вес.
      3. Вектор B: Dir(цель)   → Hard-аспект → Nat(ASC|MC) — вес × 0.8.
      4. Если нет ни одного ключевого аспекта (первичный управитель ↔ оси) — штраф NOISE_PENALTY.
    """
    planet_map = {p["name"]: p["abs_pos"] for p in natal_planets if "abs_pos" in p}
    start_min  = _time_to_minutes(start_time)
    end_min    = _time_to_minutes(end_time)

    # Предрасчёт дуг (не зависят от времени рождения)
    prepared_events: List[Dict] = []
    for ev in events:
        try:
            arc_deg, _ = calculate_direction_arc(natal_inp, ev["target_date"], mode=mode)
            prepared_events.append({
                "event":      ev,
                "arc_deg":    arc_deg,
                "weight":     float(ev.get("weight", 1.0)),
                "event_type": ev["event_type"],
            })
        except Exception as exc:
            print(f"[RECTIFY] Ошибка расчёта дуги для {ev.get('target_date')}: {exc}")

    if not prepared_events:
        return {"meta": {"type": "rectification_strict"}, "top_hypotheses": []}

    daily_grids = generate_window_grids(natal_inp, start_min, end_min)
    minute_scores: List[Dict] = []

    for grid in daily_grids:
        minute_rulers = grid["rulers"]
        total_score   = 0.0
        all_matches:  List[Dict] = []
        had_key_hit   = False      # флаг: есть ли ключевой аспект (первичный управитель × ось)

        for prep in prepared_events:
            ev_type   = prep["event_type"]
            arc_deg   = prep["arc_deg"]
            ev_weight = prep["weight"]

            targets, primary_planets = build_strict_targets(ev_type, minute_rulers, planet_map)

            for target in targets:
                p_name   = target["name"]
                nat_pos  = target["abs_pos"]
                t_weight = target["weight"]
                is_prim  = target["is_primary"]

                # ── Вектор A: Dir(ASC/MC) → Hard-аспект → Nat(цель) ──────────────
                for angle_name in DIRECTED_ANGLES:
                    dir_angle = (grid[angle_name] + arc_deg) % 360.0

                    result = _check_aspect(dir_angle, nat_pos, ALL_ASPECTS, max_orb)
                    if result:
                        asp, orb = result
                        hit = (max_orb - orb) * asp["weight"] * t_weight * ev_weight
                        total_score += hit
                        if is_prim:
                            had_key_hit = True
                        all_matches.append({
                            "event_type":  ev_type,
                            "target_date": prep["event"]["target_date"],
                            "directed":    f"Dir {angle_name}",
                            "natal":       f"Nat {p_name}",
                            "aspect":      asp["name"],
                            "arc_deg":     round(arc_deg, 3),
                            "orb":         round(orb, 4),
                            "score":       round(hit, 4),
                            "key":         is_prim,
                        })

                # ── Вектор B: Dir(цель) → Hard-аспект → Nat(ASC/MC) ──────────────
                dir_planet = (nat_pos + arc_deg) % 360.0
                for angle_name in DIRECTED_ANGLES:
                    nat_angle = grid[angle_name]

                    result = _check_aspect(dir_planet, nat_angle, ALL_ASPECTS, max_orb)
                    if result:
                        asp, orb = result
                        hit = (max_orb - orb) * asp["weight"] * t_weight * ev_weight * 0.8
                        total_score += hit
                        if is_prim:
                            had_key_hit = True
                        all_matches.append({
                            "event_type":  ev_type,
                            "target_date": prep["event"]["target_date"],
                            "directed":    f"Dir {p_name}",
                            "natal":       f"Nat {angle_name}",
                            "aspect":      asp["name"],
                            "arc_deg":     round(arc_deg, 3),
                            "orb":         round(orb, 4),
                            "score":       round(hit, 4),
                            "key":         is_prim,
                        })

        # ── Штраф за шум: нет ни одного ключевого аспекта ────────────────────
        if total_score > 0 and not had_key_hit:
            total_score *= NOISE_PENALTY
            for m in all_matches:
                m["noise_penalty"] = True

        if total_score > 0:
            minute_scores.append({
                "time":            grid["time"],
                "Ascendant":       round(grid["Ascendant"], 4),
                "Medium_Coeli":    round(grid["Medium_Coeli"], 4),
                "Descendant":      round(grid["Descendant"], 4),
                "Imum_Coeli":      round(grid["Imum_Coeli"], 4),
                "ascendant_sign":  lon_to_sign(grid["Ascendant"]),
                "asc_sign":        lon_to_sign(grid["Ascendant"]),
                "mc_sign":         lon_to_sign(grid["Medium_Coeli"]),
                "total_score":     round(total_score, 4),
                "raw_score":       round(total_score, 4),
                "had_key_hit":     had_key_hit,
                "matches":         all_matches,
            })

    minute_scores.sort(key=lambda x: x["total_score"], reverse=True)

    if minute_scores:
        top_raw = minute_scores[0]["total_score"]
        for m in minute_scores:
            if top_raw > 0:
                m["score"] = round(min(100.0, (m["total_score"] / top_raw) * 100.0), 1)
            else:
                m["score"] = 0.0

    return {
        "meta": {
            "type":             "rectification_strict",
            "target":           natal_inp.name,
            "mode":             mode,
            "max_orb":          max_orb,
            "window":           f"{start_time} – {end_time}",
            "events_processed": len(prepared_events),
            "noise_penalty":    NOISE_PENALTY,
        },
        "top_hypotheses": minute_scores[:10],
    }