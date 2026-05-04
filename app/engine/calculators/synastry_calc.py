from typing import Any, Dict, List
from app.engine.core.utils import get_house_for_degree

# 🔥 ПОЛНЫЙ СЛОВАРЬ АСПЕКТОВ (Мажорные + Минорные)
ASPECT_ANGLES = {
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

# Множество минорных аспектов для быстрой проверки
MINOR_ASPECTS = {"Quincunx", "Sesquiquadrate", "Semisquare", "Semisextile", "Quintile", "Biquintile"}

def get_orb_limit(p1_name: str, p2_name: str, aspect_name: str) -> float:
    """Определяет допустимый орбис с учетом планет и ТИПА аспекта"""
    pair = {p1_name, p2_name}
    has_luminary = "Sun" in pair or "Moon" in pair
    
    # 🔥 ЖЕСТКИЕ ОРБИСЫ ДЛЯ МИНОРНЫХ АСПЕКТОВ
    if aspect_name in MINOR_ASPECTS:
        # Светилам даем чуть больше поблажек (1.5 градуса), остальным - жестко 1 градус
        if has_luminary:
            return 1.5
        return 1.0

    # 🔥 ОРБИСЫ ДЛЯ МАЖОРНЫХ АСПЕКТОВ
    # Светила (Солнце, Луна)
    if has_luminary:
        return 7.0
    # Личные планеты
    elif pair.intersection({"Mercury", "Venus", "Mars"}):
        return 5.0
    # Социальные
    elif pair.intersection({"Jupiter", "Saturn"}):
        return 4.0
    # Астероиды, Фиктивные точки, Узлы, Углы - очень узкий орбис даже для мажорных
    elif pair.intersection({
        "True_North_Lunar_Node", "Mean_North_Lunar_Node", "True_South_Lunar_Node", "Mean_South_Lunar_Node",
        "Lilith", "Mean_Lilith", "Chiron", "Ceres", "Pallas", "Juno", "Vesta",
        "Ascendant", "Descendant", "Medium_Coeli", "Imum_Coeli", "Vertex", "Fortune"
    }):
        return 2.0
    
    # По умолчанию для высших
    return 3.0

def get_synastry_aspects(planets1: List[Any], planets2: List[Any]) -> List[Dict[str, Any]]:
    """Рассчитывает аспекты напрямую между двумя массивами обогащенных планет"""
    aspects = []
    
    # 🔥 Универсальный экстрактор данных (понимает dict, объекты Kerykeion и кортежи)
    def extract_data(p_raw):
        p = p_raw[1] if isinstance(p_raw, tuple) else p_raw
        if isinstance(p, dict):
            return p.get("name"), p.get("abs_pos")
        return getattr(p, "name", None), getattr(p, "abs_pos", None)

    for p1_raw in planets1:
        p1_name, p1_pos = extract_data(p1_raw)
        
        # 🔥 Пропускаем пустые данные и ТОЧКИ ДОМОВ (First_House и т.д.)
        if not p1_name or p1_pos is None or "house" in p1_name.lower():
            continue

        for p2_raw in planets2:
            p2_name, p2_pos = extract_data(p2_raw)
            
            # 🔥 Пропускаем пустые данные и ТОЧКИ ДОМОВ во второй карте
            if not p2_name or p2_pos is None or "house" in p2_name.lower():
                continue

            # Вычисляем кратчайшее расстояние между двумя градусами на круге
            diff = abs(p1_pos - p2_pos)
            if diff > 180:
                diff = 360 - diff
                
            # Проверяем попадание во все аспекты
            for aspect_name, angle in ASPECT_ANGLES.items():
                orb = abs(diff - angle)
                # Передаем тип аспекта в функцию расчета лимитов
                limit = get_orb_limit(p1_name, p2_name, aspect_name)
                
                if orb <= limit:
                    aspects.append({
                        "person1_object": p1_name,
                        "aspect": aspect_name,
                        "person2_object": p2_name,
                        "orb": round(orb, 2),
                    })
                    
    return aspects

def calculate_house_overlays(planets: List[Dict], partner_houses: List[Dict]) -> List[Dict]:
    """Рассчитывает попадание планет одного человека в дома партнера"""
    overlays = []
    for p in planets:
        house_in_partner = get_house_for_degree(p["abs_pos"], partner_houses)
        
        # Защита от выхода за пределы массива
        house_sign = ""
        if 1 <= house_in_partner <= len(partner_houses):
            house_sign = partner_houses[house_in_partner - 1]["sign"]
            
        overlays.append({
            "planet": p["name"],
            "in_partner_house": house_in_partner,
            "partner_house_sign": house_sign
        })
    return overlays