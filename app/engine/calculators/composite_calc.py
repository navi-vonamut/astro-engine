from typing import Any, Dict, List

def calculate_midpoint(pos1: float, pos2: float) -> float:
    """Вычисляет среднюю точку между двумя координатами (0-360) по кратчайшей дуге"""
    diff = abs(pos1 - pos2)
    
    if diff <= 180:
        midpoint = (pos1 + pos2) / 2
    else:
        # Если расстояние больше 180, средняя точка на другой стороне
        midpoint = (pos1 + pos2 + 360) / 2
        
    return midpoint % 360

def get_composite_planets(planets1: List[Dict], planets2: List[Dict]) -> List[Dict]:
    """Генерирует список композитных планет методом мидпойнтов"""
    composite_planets = []
    
    # Создаем мапу для быстрого поиска планет партнера
    p2_map = {p["name"]: p for p in planets2}
    
    for p1 in planets1:
        name = p1["name"]
        if name in p2_map:
            p2 = p2_map[name]
            
            mid_pos = calculate_midpoint(p1["abs_pos"], p2["abs_pos"])
            
            # Для композита мы не считаем скорость и ретроградность (это статика),
            # но определяем знак и градус
            sign_id = int(mid_pos // 30)
            from app.engine.core.constants import SIGNS_SHORT
            
            composite_planets.append({
                "name": name,
                "abs_pos": round(mid_pos, 4),
                "degree": round(mid_pos % 30, 4),
                "sign_id": sign_id,
                "sign": SIGNS_SHORT[sign_id]
            })
            
    return composite_planets

def get_composite_houses(houses1: List[Dict], houses2: List[Dict]) -> List[Dict]:
    """Вычисляет композитную сетку домов по мидпойнтам куспидов"""
    composite_houses = []
    
    for h1, h2 in zip(houses1, houses2):
        mid_pos = calculate_midpoint(h1["abs_pos"], h2["abs_pos"])
        sign_id = int(mid_pos // 30)
        from app.engine.core.constants import SIGNS_SHORT
        
        composite_houses.append({
            "house": h1["house"],
            "abs_pos": round(mid_pos, 4),
            "degree": round(mid_pos % 30, 4),
            "sign": SIGNS_SHORT[sign_id]
        })
        
    return composite_houses

def calculate_composite_balance(planets: List[Dict]) -> Dict[str, Any]:
    """Рассчитывает распределение стихий и качеств на основе весов планет"""
    
    # Таблица весов планет для баланса
    WEIGHTS = {
        "Sun": 4, "Moon": 4, 
        "Mercury": 2, "Venus": 2, "Mars": 2,
        "Ascendant": 3, "Medium_Coeli": 2, # Углы тоже важны
        "Jupiter": 1, "Saturn": 1, "Uranus": 1, "Neptune": 1, "Pluto": 1
    }

    # Маппинг знаков (0-11) к стихиям и качествам
    # 0: Fire/Card (Ari), 1: Earth/Fix (Tau), 2: Air/Mut (Gem)...
    ELEMENT_MAP = ["fire", "earth", "air", "water"] * 3
    QUALITY_MAP = ["cardinal", "fixed", "mutable"] * 4

    elements = {"fire": 0.0, "earth": 0.0, "air": 0.0, "water": 0.0}
    qualities = {"cardinal": 0.0, "fixed": 0.0, "mutable": 0.0}
    
    total_points = 0.0

    for p in planets:
        name = p["name"]
        if name in WEIGHTS:
            weight = WEIGHTS[name]
            sign_id = p["sign_id"]
            
            elements[ELEMENT_MAP[sign_id]] += weight
            qualities[QUALITY_MAP[sign_id]] += weight
            total_points += weight

    # Считаем проценты
    def to_percent(data, total):
        if total == 0: return data
        res = data.copy()
        for k, v in data.items():
            res[f"{k}_percentage"] = round((v / total) * 100)
        return res

    return {
        "elements": to_percent(elements, total_points),
        "qualities": to_percent(qualities, total_points)
    }