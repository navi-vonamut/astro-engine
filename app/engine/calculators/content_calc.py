import swisseph as swe
import datetime
from typing import Dict, List, Any
import math

# Импортируем ваши константы
from app.engine.core.constants import SIGNS_SHORT, SWISSEPH_OBJECTS, ASPECT_RULES

# Маппинг знаков в их порядковый номер (0-11)
SIGN_TO_ID = {sign: i for i, sign in enumerate(SIGNS_SHORT)}

# Категоризация объектов для удобства фронтенда и ИИ
CATEGORIES = {
    "planets": ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"],
    "asteroids": ["Chiron", "Ceres", "Pallas", "Juno", "Vesta"],
    "points": ["True_North_Lunar_Node", "True_South_Lunar_Node", "Mean_Lilith"]
}

# Для фоновых событий (чтобы не спамить ИИ) берем только мажорные аспекты
MAJOR_ASPECTS = {
    0: "conjunction",
    60: "sextile",
    90: "square",
    120: "trine",
    180: "opposition"
}

# 🔥 МИНОРНЫЕ АСПЕКТЫ (только для фронтенда)
MINOR_ASPECTS = {
    30: "semisextile",
    45: "semisquare",
    72: "quintile",
    135: "sesquiquadrate",
    144: "biquintile",
    150: "quincunx"
}

def get_solar_house(planet_sign_id: int, target_sign_id: int) -> int:
    """Рассчитывает номер дома по системе Whole Sign."""
    return ((planet_sign_id - target_sign_id) % 12) + 1

def get_angular_distance(lon1: float, lon2: float) -> float:
    """Кратчайшее угловое расстояние между двумя точками на круге."""
    diff = abs(lon1 - lon2)
    return diff if diff <= 180 else 360 - diff

def get_signed_orb(lon1: float, lon2: float, aspect: float) -> float:
    """Считает орбис со знаком (от -180 до +180), чтобы ловить момент пересечения аспекта"""
    diff = (lon1 - lon2) % 360
    # Для соединения и оппозиции цель одна, для остальных (секстиль, квадрат) — две (например 90 и 270)
    targets = [aspect] if aspect in [0, 180] else [aspect, 360 - aspect]
    
    best_orb = 999.0
    for t in targets:
        d = (diff - t + 180) % 360 - 180
        if abs(d) < abs(best_orb):
            best_orb = d
    return best_orb

def generate_content_events(target_sign: str, start_date: str, end_date: str) -> Dict[str, Any]:
    """Сканирует период и собирает мощные астро-события для ИИ-генерации"""
    target_sign_id = SIGN_TO_ID.get(target_sign.capitalize()[:3], 0)
    
    start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d")
    delta_days = (end_dt - start_dt).days
    delta_days = min(delta_days, 730) 

    # Все объекты, которые мы будем трекать
    TRACKED_OBJECTS = CATEGORIES["planets"] + CATEGORIES["asteroids"] + ["True_North_Lunar_Node", "Mean_Lilith"]
    
    events = {
        "ingresses": [],
        "stations": [],
        "aspects": [],
        "minor_aspects": [], # 🔥 Новый массив
        "lunar_phases": []
    }
    start_positions = []
    prev_state = {}
    
    for day_offset in range(-1, delta_days + 1):
        curr_dt = start_dt + datetime.timedelta(days=day_offset)
        jd = swe.julday(curr_dt.year, curr_dt.month, curr_dt.day, 12.0)
        
        day_positions = {}
        
        for p_name in TRACKED_OBJECTS:
            pid = SWISSEPH_OBJECTS.get(p_name)
            if pid is None: continue
                
            res = swe.calc_ut(jd, pid, swe.FLG_SWIEPH | swe.FLG_SPEED)
            lon = res[0][0]
            speed = res[0][3]
            
            sign_id = int(lon // 30)
            is_retro = speed < 0
            solar_house = get_solar_house(sign_id, target_sign_id)
            
            # Присваиваем категорию
            cat = "planets"
            if p_name in CATEGORIES["asteroids"]: cat = "asteroids"
            elif p_name in CATEGORIES["points"]: cat = "points"

            day_positions[p_name] = {
                "lon": lon,
                "sign_id": sign_id,
                "sign": SIGNS_SHORT[sign_id],
                "solar_house": solar_house,
                "is_retro": is_retro,
                "category": cat
            }

        # Добавляем Южный Узел вручную (напротив Северного)
        nn = day_positions.get("True_North_Lunar_Node")
        if nn:
            sn_lon = (nn["lon"] + 180) % 360
            sn_sign_id = int(sn_lon // 30)
            day_positions["True_South_Lunar_Node"] = {
                "lon": sn_lon,
                "sign_id": sn_sign_id,
                "sign": SIGNS_SHORT[sn_sign_id],
                "solar_house": get_solar_house(sn_sign_id, target_sign_id),
                "is_retro": nn["is_retro"],
                "category": "points"
            }

        # --- ЗАПИСЬ СТАРТОВЫХ ПОЗИЦИЙ (ТОЛЬКО ДЛЯ 0 ДНЯ) ---
        if day_offset == 0:
            for p_name, data in day_positions.items():
                start_positions.append({
                    "planet": p_name,
                    "category": data["category"],
                    "sign": data["sign"],
                    "solar_house": data["solar_house"],
                    "is_retro": data["is_retro"]
                })
        
        # --- ПОИСК СОБЫТИЙ ---
        if day_offset >= 0 and prev_state:
            # 1. Ингрессии и развороты
            for p_name, data in day_positions.items():
                prev_data = prev_state.get(p_name)
                if not prev_data: continue
                
                # Ингрессия
                if prev_data["sign_id"] != data["sign_id"]:
                    events["ingresses"].append({
                        "date": curr_dt.strftime("%Y-%m-%d"),
                        "planet": p_name,
                        "event_type": "ingress",
                        "from_sign": SIGNS_SHORT[prev_data["sign_id"]],
                        "to_sign": data["sign"],
                        "to_solar_house": data["solar_house"]
                    })
                    
                # Разворот (игнорируем Солнце, Луну и Узлы)
                if p_name not in ["Sun", "Moon"] and "Node" not in p_name:
                    if prev_data["is_retro"] != data["is_retro"]:
                        direction = "retrograde" if data["is_retro"] else "direct"
                        events["stations"].append({
                            "date": curr_dt.strftime("%Y-%m-%d"),
                            "planet": p_name,
                            "event_type": "station",
                            "direction": direction,
                            "in_solar_house": data["solar_house"],
                            "in_sign": data["sign"]
                        })

            # 2. Фоновые точные аспекты
            object_names = list(day_positions.keys())
            for i in range(len(object_names)):
                for j in range(i + 1, len(object_names)):
                    p1, p2 = object_names[i], object_names[j]
                    if "Node" in p1 and "Node" in p2: continue

                    lon1_curr, lon2_curr = day_positions[p1]["lon"], day_positions[p2]["lon"]
                    lon1_prev, lon2_prev = prev_state[p1]["lon"], prev_state[p2]["lon"]

                    # Сначала проверяем МАЖОРНЫЕ аспекты
                    for angle, name in MAJOR_ASPECTS.items():
                        orb_prev = get_signed_orb(lon1_prev, lon2_prev, angle)
                        orb_curr = get_signed_orb(lon1_curr, lon2_curr, angle)
                        
                        if (orb_prev * orb_curr <= 0) and abs(orb_prev - orb_curr) < 30:
                            if {"Sun", "Moon"} == {p1, p2}:
                                if angle == 0:
                                    events["lunar_phases"].append({"date": curr_dt.strftime("%Y-%m-%d"), "event_type": "lunar_phase", "phase": "New Moon", "sign": day_positions["Moon"]["sign"], "solar_house": day_positions["Moon"]["solar_house"]})
                                    continue
                                elif angle == 180:
                                    events["lunar_phases"].append({"date": curr_dt.strftime("%Y-%m-%d"), "event_type": "lunar_phase", "phase": "Full Moon", "sign": day_positions["Moon"]["sign"], "solar_house": day_positions["Moon"]["solar_house"]})
                                    continue
                            
                            events["aspects"].append({
                                "date": curr_dt.strftime("%Y-%m-%d"),
                                "p1": p1, "p2": p2, "aspect": name,
                                "p1_house": day_positions[p1]["solar_house"], "p2_house": day_positions[p2]["solar_house"]
                            })

                    # 🔥 Теперь проверяем МИНОРНЫЕ аспекты
                    for angle, name in MINOR_ASPECTS.items():
                        orb_prev = get_signed_orb(lon1_prev, lon2_prev, angle)
                        orb_curr = get_signed_orb(lon1_curr, lon2_curr, angle)
                        
                        if (orb_prev * orb_curr <= 0) and abs(orb_prev - orb_curr) < 15:
                            events["minor_aspects"].append({
                                "date": curr_dt.strftime("%Y-%m-%d"),
                                "p1": p1, "p2": p2, "aspect": name,
                                "p1_house": day_positions[p1]["solar_house"], "p2_house": day_positions[p2]["solar_house"]
                            })
        
        prev_state = day_positions
            
    return {
        "meta": {
            "target_sign": target_sign.capitalize()[:3],
            "start_date": start_date,
            "end_date": end_date
        },
        "start_positions": start_positions,
        "events": events
    }

def get_lunar_day(moon_lon: float, sun_lon: float) -> int:
    """Рассчитывает лунный день (каждые 12 градусов отхождения Луны от Солнца)"""
    diff = (moon_lon - sun_lon) % 360
    return int(diff // 12) + 1

def find_voc_start(ingress_dt: datetime.datetime) -> dict:
    """
    Ищет начало Холостой Луны (Void of Course).
    Шагает назад во времени от момента ингрессии, пока не найдет 
    последний мажорный аспект Луны к любой из главных планет.
    """
    MAJOR_PLANETS = ["Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]
    TARGET_ASPECTS = [0, 60, 90, 120, 180]
    
    curr_dt = ingress_dt
    step = datetime.timedelta(minutes=5) # Шаг в 5 минут для высокой точности
    
    jd_curr = swe.julday(curr_dt.year, curr_dt.month, curr_dt.day, curr_dt.hour + curr_dt.minute/60.0)
    
    # Записываем изначальные дистанции от Луны до планет в момент ингрессии
    prev_dists = {}
    moon_pos = swe.calc_ut(jd_curr, SWISSEPH_OBJECTS["Moon"])[0][0]
    
    for p_name in MAJOR_PLANETS:
        p_pos = swe.calc_ut(jd_curr, SWISSEPH_OBJECTS[p_name])[0][0]
        diff = abs(moon_pos - p_pos)
        if diff > 180: diff = 360 - diff
        prev_dists[p_name] = diff
        
    # Шагаем назад до 3 суток (864 итерации по 5 минут)
    for _ in range(864):
        curr_dt -= step
        jd_curr = swe.julday(curr_dt.year, curr_dt.month, curr_dt.day, curr_dt.hour + curr_dt.minute/60.0)
        
        moon_pos = swe.calc_ut(jd_curr, SWISSEPH_OBJECTS["Moon"])[0][0]
        for p_name in MAJOR_PLANETS:
            p_pos = swe.calc_ut(jd_curr, SWISSEPH_OBJECTS[p_name])[0][0]
            diff = abs(moon_pos - p_pos)
            if diff > 180: diff = 360 - diff
            
            old_dist = prev_dists[p_name]
            
            # Если между старым и новым шагом мы пересекли точный градус аспекта (0, 60, 90, 120, 180)
            for asp in TARGET_ASPECTS:
                if (old_dist - asp) * (diff - asp) <= 0:
                    # МЫ НАШЛИ ПОСЛЕДНИЙ АСПЕКТ!
                    return {
                        "voc_start": curr_dt.strftime("%Y-%m-%dT%H:%M:%S"),
                        "last_aspect": MAJOR_ASPECTS[asp],
                        "planet": p_name
                    }
            prev_dists[p_name] = diff
            
    return None

def generate_lunar_calendar(start_date: str, end_date: str) -> Dict[str, Any]:
    """Генерирует лунный календарь: фазы, дни, ингрессии и Холостую Луну (VOC)"""
    start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d")
    delta_days = (end_dt - start_dt).days

    daily_info = []
    voc_periods = []
    
    prev_sign_id = None
    
    # 1. Сначала сканируем ингрессии Луны с шагом в 15 минут для поиска Холостой Луны
    curr_scan = start_dt
    scan_end = end_dt + datetime.timedelta(days=1)
    
    jd = swe.julday(curr_scan.year, curr_scan.month, curr_scan.day, curr_scan.hour)
    moon_lon = swe.calc_ut(jd, SWISSEPH_OBJECTS["Moon"])[0][0]
    prev_sign_id = int(moon_lon // 30)
    
    while curr_scan <= scan_end:
        curr_scan += datetime.timedelta(minutes=15)
        jd = swe.julday(curr_scan.year, curr_scan.month, curr_scan.day, curr_scan.hour + curr_scan.minute/60.0)
        moon_lon = swe.calc_ut(jd, SWISSEPH_OBJECTS["Moon"])[0][0]
        curr_sign_id = int(moon_lon // 30)
        
        # Если Луна сменила знак
        if curr_sign_id != prev_sign_id:
            ingress_time = curr_scan
            voc_data = find_voc_start(ingress_time)
            
            if voc_data:
                voc_periods.append({
                    "voc_start": voc_data["voc_start"],
                    "voc_end": ingress_time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "ingress_sign": SIGNS_SHORT[curr_sign_id],
                    "last_aspect": f"{voc_data['last_aspect']} with {voc_data['planet']}"
                })
            prev_sign_id = curr_sign_id

    # 2. Генерируем информацию на каждый день (на 12:00 по UTC)
    for day_offset in range(delta_days + 1):
        curr_dt = start_dt + datetime.timedelta(days=day_offset)
        jd = swe.julday(curr_dt.year, curr_dt.month, curr_dt.day, 12.0)
        
        moon_lon = swe.calc_ut(jd, SWISSEPH_OBJECTS["Moon"])[0][0]
        sun_lon = swe.calc_ut(jd, SWISSEPH_OBJECTS["Sun"])[0][0]
        
        sign_id = int(moon_lon // 30)
        lunar_day = get_lunar_day(moon_lon, sun_lon)
        
        # Быстрый расчет процента освещенности (от 0 до 100)
        illumination = 50 * (1 - swe.calc_ut(jd, SWISSEPH_OBJECTS["Moon"])[0][0] * 0) # Упрощенно
        
        # Корректный расчет освещенности через отхождение
        diff = (moon_lon - sun_lon) % 360
        phase_percent = round((1 - math.cos(math.radians(diff))) / 2 * 100, 1)

        daily_info.append({
            "date": curr_dt.strftime("%Y-%m-%d"),
            "lunar_day": lunar_day,
            "moon_sign": SIGNS_SHORT[sign_id],
            "illumination_percent": phase_percent
        })

    return {
        "meta": {
            "start_date": start_date,
            "end_date": end_date
        },
        "daily_lunar_calendar": daily_info,
        "void_of_course_periods": voc_periods
    }