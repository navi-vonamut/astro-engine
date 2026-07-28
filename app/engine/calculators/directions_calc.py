import datetime
import swisseph as swe
from typing import Dict, List, Any, Tuple
from app.engine.core.models import BirthInput
from app.engine.calculators.solar_calc import get_utc_jd
from app.engine.core.constants import SIGNS_SHORT
from app.engine.core.utils import get_house_for_degree

# Аспекты для дирекций
DIRECTION_ASPECT_ANGLES = {
    "Conjunction": 0.0,
    "Opposition": 180.0,
    "Trine": 120.0,
    "Square": 90.0,
    "Sextile": 60.0,
    "Quincunx": 150.0,
    "Sesquiquadrate": 135.0,
    "Semisquare": 45.0,
    "Semisextile": 30.0,
    "Quintile": 72.0,
    "Biquintile": 144.0
}

MAJOR_ASPECTS = {"Conjunction", "Opposition", "Trine", "Square", "Sextile"}

def calculate_direction_arc(natal_inp: BirthInput, target_date: str, mode: str = "symbolic") -> Tuple[float, float]:
    """
    Рассчитывает дугу дирекции в градусах и возраст пользователя в годах.
    mode: 'symbolic' (1° = 1 год) или 'solar_arc' (дуга движения Солнца).
    """
    natal_jd_utc = get_utc_jd(natal_inp)
    
    y_t, m_t, d_t = map(int, target_date.split('-'))
    target_jd_utc = swe.julday(y_t, m_t, d_t, 12.0)
    
    TROPICAL_YEAR = 365.242199
    age_in_years = (target_jd_utc - natal_jd_utc) / TROPICAL_YEAR
    
    if mode == "solar_arc":
        # Вычисляем прохождение Солнца
        sun_natal, _ = swe.calc_ut(natal_jd_utc, swe.SUN)
        sun_target, _ = swe.calc_ut(target_jd_utc, swe.SUN)
        arc_degrees = (sun_target[0] - sun_natal[0]) % 360.0
    else:
        # Символические дирекции: 1° = 1 тропический год
        arc_degrees = age_in_years

    return arc_degrees, age_in_years


def calculate_directed_chart(natal_planets: List[Dict[str, Any]], natal_houses: List[Dict[str, Any]], arc_degrees: float) -> Dict[str, Any]:
    """
    Сдвигает все планеты и куспиды домов натальной карты на дугу дирекции (arc_degrees).
    """
    directed_planets = []
    for p in natal_planets:
        dir_pos = (p["abs_pos"] + arc_degrees) % 360.0
        sign_num = int(dir_pos // 30)
        deg_in_sign = dir_pos % 30.0
        
        # Находим натальный дом, в который попала дирекционная планета
        house_num = get_house_for_degree(dir_pos, natal_houses)
        
        directed_planets.append({
            "name": p["name"],
            "sign": SIGNS_SHORT[sign_num] if sign_num < len(SIGNS_SHORT) else "",
            "sign_id": sign_num,
            "degree": deg_in_sign,
            "abs_pos": round(dir_pos, 4),
            "house": house_num,
            "is_retro": p.get("is_retro", False),
            "speed": p.get("speed", 0.0)
        })

    directed_houses = []
    for h in natal_houses:
        dir_pos = (h["abs_pos"] + arc_degrees) % 360.0
        sign_num = int(dir_pos // 30)
        deg_in_sign = dir_pos % 30.0

        directed_houses.append({
            "house": h["house"],
            "name": h.get("name", f"House_{h['house']}"),
            "sign": SIGNS_SHORT[sign_num] if sign_num < len(SIGNS_SHORT) else "",
            "sign_id": sign_num,
            "degree": deg_in_sign,
            "abs_pos": round(dir_pos, 4)
        })

    return {
        "planets": directed_planets,
        "houses": directed_houses
    }


def calculate_directional_aspects(
    directed_planets: List[Dict[str, Any]],
    directed_houses: List[Dict[str, Any]],
    natal_planets: List[Dict[str, Any]],
    natal_houses: List[Dict[str, Any]],
    max_orb: float = 1.0
) -> List[Dict[str, Any]]:
    """
    Рассчитывает дирекционные аспекты между:
    1. Дирекционными планетами и Натальными планетами
    2. Дирекционными планетами и Натальными куспидами домов
    3. Дирекционными куспидами домов (Asc, MC и др.) и Натальными планетами
    """
    aspects = []

    # 1. Дирекционные планеты -> Натальные планеты
    for dp in directed_planets:
        for np in natal_planets:
            diff = abs(dp["abs_pos"] - np["abs_pos"]) % 360.0
            if diff > 180.0:
                diff = 360.0 - diff

            for aspect_name, target_angle in DIRECTION_ASPECT_ANGLES.items():
                orb = abs(diff - target_angle)
                if orb <= max_orb:
                    aspects.append({
                        "directed_point": dp["name"],
                        "directed_type": "planet",
                        "natal_point": np["name"],
                        "natal_type": "planet",
                        "aspect": aspect_name,
                        "angle": target_angle,
                        "orb": round(orb, 4),
                        "exactness": round(1.0 - (orb / max_orb), 2),
                        "is_major": aspect_name in MAJOR_ASPECTS
                    })

    # 2. Дирекционные планеты -> Натальные дома (углы и куспиды)
    for dp in directed_planets:
        for nh in natal_houses:
            diff = abs(dp["abs_pos"] - nh["abs_pos"]) % 360.0
            if diff > 180.0:
                diff = 360.0 - diff

            h_name = f"House_{nh['house']}"
            if nh["house"] == 1: h_name = "Ascendant"
            elif nh["house"] == 10: h_name = "Medium_Coeli"
            elif nh["house"] == 7: h_name = "Descendant"
            elif nh["house"] == 4: h_name = "Imum_Coeli"

            for aspect_name, target_angle in DIRECTION_ASPECT_ANGLES.items():
                orb = abs(diff - target_angle)
                if orb <= max_orb:
                    aspects.append({
                        "directed_point": dp["name"],
                        "directed_type": "planet",
                        "natal_point": h_name,
                        "natal_type": "house",
                        "aspect": aspect_name,
                        "angle": target_angle,
                        "orb": round(orb, 4),
                        "exactness": round(1.0 - (orb / max_orb), 2),
                        "is_major": aspect_name in MAJOR_ASPECTS
                    })

    # 3. Дирекционные дома -> Натальные планеты
    for dh in directed_houses:
        h_name = f"House_{dh['house']}"
        if dh["house"] == 1: h_name = "Ascendant"
        elif dh["house"] == 10: h_name = "Medium_Coeli"
        elif dh["house"] == 7: h_name = "Descendant"
        elif dh["house"] == 4: h_name = "Imum_Coeli"

        for np in natal_planets:
            diff = abs(dh["abs_pos"] - np["abs_pos"]) % 360.0
            if diff > 180.0:
                diff = 360.0 - diff

            for aspect_name, target_angle in DIRECTION_ASPECT_ANGLES.items():
                orb = abs(diff - target_angle)
                if orb <= max_orb:
                    aspects.append({
                        "directed_point": h_name,
                        "directed_type": "house",
                        "natal_point": np["name"],
                        "natal_type": "planet",
                        "aspect": aspect_name,
                        "angle": target_angle,
                        "orb": round(orb, 4),
                        "exactness": round(1.0 - (orb / max_orb), 2),
                        "is_major": aspect_name in MAJOR_ASPECTS
                    })

    # Сортируем аспекты по точнейшему орбису
    aspects.sort(key=lambda a: a["orb"])
    return aspects
