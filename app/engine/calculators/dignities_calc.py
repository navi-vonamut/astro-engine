from typing import Dict, Any, Optional

# Классические управители знаков (Обитель)
DOMICILES = {
    0: "Mars", 1: "Venus", 2: "Mercury", 3: "Moon", 4: "Sun", 5: "Mercury",
    6: "Venus", 7: "Mars", 8: "Jupiter", 9: "Saturn", 10: "Saturn", 11: "Jupiter"
}

# Экзальтации (знак: планета)
EXALTATIONS = {
    0: "Sun", 1: "Moon", 3: "Jupiter", 5: "Mercury", 6: "Saturn", 9: "Mars", 11: "Venus"
}

# Триплицитеты (по Доротею Сидонскому / Лилли). Формат: {стихия_id: {"day": планета, "night": планета}}
# 0 - Огонь (0, 4, 8), 1 - Земля (1, 5, 9), 2 - Воздух (2, 6, 10), 3 - Вода (3, 7, 11)
TRIPLICITIES = {
    0: {"day": "Sun", "night": "Jupiter"},
    1: {"day": "Venus", "night": "Moon"},
    2: {"day": "Saturn", "night": "Mercury"},
    3: {"day": "Mars", "night": "Mars"}
}

# Термы Птолемея. Формат: знак_id: [(до_градуса, "Планета"), ...]
TERMS = {
    0: [(6, "Jupiter"), (14, "Venus"), (21, "Mercury"), (26, "Mars"), (30, "Saturn")],
    1: [(8, "Venus"), (15, "Mercury"), (22, "Jupiter"), (26, "Saturn"), (30, "Mars")],
    2: [(7, "Mercury"), (14, "Jupiter"), (21, "Venus"), (25, "Saturn"), (30, "Mars")],
    3: [(6, "Mars"), (13, "Jupiter"), (20, "Mercury"), (27, "Venus"), (30, "Saturn")],
    4: [(6, "Saturn"), (13, "Mercury"), (19, "Venus"), (25, "Jupiter"), (30, "Mars")],
    5: [(7, "Mercury"), (13, "Venus"), (18, "Jupiter"), (24, "Saturn"), (30, "Mars")],
    6: [(6, "Saturn"), (11, "Venus"), (19, "Jupiter"), (24, "Mercury"), (30, "Mars")],
    7: [(6, "Mars"), (14, "Jupiter"), (21, "Venus"), (27, "Mercury"), (30, "Saturn")],
    8: [(8, "Jupiter"), (14, "Venus"), (19, "Mercury"), (25, "Saturn"), (30, "Mars")],
    9: [(6, "Venus"), (12, "Mercury"), (19, "Jupiter"), (25, "Mars"), (30, "Saturn")],
    10: [(6, "Saturn"), (12, "Mercury"), (20, "Venus"), (25, "Jupiter"), (30, "Mars")],
    11: [(8, "Venus"), (14, "Jupiter"), (20, "Mercury"), (26, "Mars"), (30, "Saturn")]
}

# Фасы (Деканы) по халдейскому ряду (каждые 10 градусов)
# Формат: знак_id: ["0-10", "10-20", "20-30"]
FACES = {
    0: ["Mars", "Sun", "Venus"],
    1: ["Mercury", "Moon", "Saturn"],
    2: ["Jupiter", "Mars", "Sun"],
    3: ["Venus", "Mercury", "Moon"],
    4: ["Saturn", "Jupiter", "Mars"],
    5: ["Sun", "Venus", "Mercury"],
    6: ["Moon", "Saturn", "Jupiter"],
    7: ["Mars", "Sun", "Venus"],
    8: ["Mercury", "Moon", "Saturn"],
    9: ["Jupiter", "Mars", "Sun"],
    10: ["Venus", "Mercury", "Moon"],
    11: ["Saturn", "Jupiter", "Mars"]
}

def get_essential_dignities(planet_name: str, sign_id: int, degree: float, is_day_chart: bool) -> Dict[str, Optional[str]]:
    """
    Возвращает планеты-управители для конкретной точки зодиака.
    """
    # 1. Обитель
    domicile = DOMICILES.get(sign_id)
    
    # 2. Экзальтация
    exaltation = EXALTATIONS.get(sign_id)
    
    # 3. Триплицитет
    element_id = sign_id % 4  # Огонь=0, Земля=1, Воздух=2, Вода=3 (Магия модульной арифметики знаков)
    time_of_day = "day" if is_day_chart else "night"
    triplicity = TRIPLICITIES[element_id][time_of_day]
    
    # 4. Терм
    term = None
    for limit, ruler in TERMS[sign_id]:
        if degree < limit:
            term = ruler
            break
            
    # 5. Фас (Декан)
    face_index = int(degree // 10)
    if face_index > 2: face_index = 2 # Защита от 30.000 градусов
    face = FACES[sign_id][face_index]
    
    # Считаем баллы достоинств (по Лилли) для текущей планеты, если она находится в этом месте
    score = 0
    if planet_name == domicile: score += 5
    if planet_name == exaltation: score += 4
    if planet_name == triplicity: score += 3
    if planet_name == term: score += 2
    if planet_name == face: score += 1
    
    # Изгнание и Падение
    detriment = DOMICILES.get((sign_id + 6) % 12) # Противоположный знак
    fall = EXALTATIONS.get((sign_id + 6) % 12)
    
    if planet_name == detriment: score -= 5
    if planet_name == fall: score -= 4

    return {
        "domicile": domicile,
        "exaltation": exaltation,
        "triplicity": triplicity,
        "term": term,
        "face": face,
        "detriment": detriment,
        "fall": fall,
        "score": score
    }