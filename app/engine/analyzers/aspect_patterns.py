import itertools
from app.engine.core.constants import ASPECT_PATTERN_NAMES # 🔥 Импортируем константы

def calculate_aspect_patterns(aspects_list):
    """Ищет замкнутые фигуры аспектов"""
    aspect_map = {}
    for a in aspects_list:
        p1, p2, a_type = a.get('p1'), a.get('p2'), a.get('type')
        if not p1 or not p2: continue
        if p1 not in aspect_map: aspect_map[p1] = {}
        if p2 not in aspect_map: aspect_map[p2] = {}
        aspect_map[p1][p2] = a_type
        aspect_map[p2][p1] = a_type

    def get_aspect(p1, p2):
        return aspect_map.get(p1, {}).get(p2)

    excluded_points = ["Ascendant", "Medium_Coeli", "Descendant", "Imum_Coeli"]
    active_planets = [p for p in aspect_map.keys() if p not in excluded_points]
    
    patterns = []
    
    # === ФИГУРЫ ИЗ 3 ПЛАНЕТ ===
    for combo in itertools.combinations(active_planets, 3):
        p1, p2, p3 = combo
        edges = [get_aspect(p1, p2), get_aspect(p1, p3), get_aspect(p2, p3)]
        
        if edges.count('opposition') == 1 and edges.count('square') == 2:
            apex = p3 if get_aspect(p1, p2) == 'opposition' else p2 if get_aspect(p1, p3) == 'opposition' else p1
            patterns.append({
                "name": ASPECT_PATTERN_NAMES["t_square"], "type": "t_square", 
                "planets": list(combo), "apex": apex
            })
            
        elif edges.count('trine') == 3:
            patterns.append({
                "name": ASPECT_PATTERN_NAMES["grand_trine"], "type": "grand_trine", 
                "planets": list(combo), "apex": None
            })
            
        elif edges.count('quincunx') == 2 and edges.count('sextile') == 1:
            apex = p3 if get_aspect(p1, p2) == 'sextile' else p2 if get_aspect(p1, p3) == 'sextile' else p1
            patterns.append({
                "name": ASPECT_PATTERN_NAMES["yod"], "type": "yod", 
                "planets": list(combo), "apex": apex
            })

    # === ФИГУРЫ ИЗ 4 ПЛАНЕТ ===
    for combo in itertools.combinations(active_planets, 4):
        p1, p2, p3, p4 = combo
        edges = [
            get_aspect(p1, p2), get_aspect(p1, p3), get_aspect(p1, p4),
            get_aspect(p2, p3), get_aspect(p2, p4), get_aspect(p3, p4)
        ]
        
        if edges.count('opposition') == 2 and edges.count('square') == 4:
            patterns.append({
                "name": ASPECT_PATTERN_NAMES["grand_cross"], "type": "grand_cross", 
                "planets": list(combo), "apex": None
            })
            
        elif edges.count('opposition') == 2 and edges.count('trine') == 2 and edges.count('sextile') == 2:
            patterns.append({
                "name": ASPECT_PATTERN_NAMES["mystic_rectangle"], "type": "mystic_rectangle", 
                "planets": list(combo), "apex": None
            })
            
        elif edges.count('trine') == 3 and edges.count('opposition') == 1 and edges.count('sextile') == 2:
            apex = None
            for p in combo:
                p_edges = [get_aspect(p, other) for other in combo if other != p]
                if p_edges.count('sextile') == 2:
                    apex = p
            patterns.append({
                "name": ASPECT_PATTERN_NAMES["kite"], "type": "kite", 
                "planets": list(combo), "apex": apex
            })

    patterns.sort(key=lambda x: len(x["planets"]), reverse=True)
    return patterns