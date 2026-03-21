import swisseph as swe
from typing import List, Dict, Any

# 🔥 ИМПОРТИРУЕМ НАШИ КОНСТАНТЫ 🔥
from app.engine.core.constants import ASPECT_RULES, STRICT_POINTS, SWISSEPH_OBJECTS

def calculate_natal_aspects(planets_list: List[Dict[str, Any]], julian_day: float) -> List[Dict[str, Any]]:
    """
    Рассчитывает все мажорные, минорные аспекты и параллели (по склонению).
    """
    clean_aspects = []
    
    def get_declination(p_name, jd):
        if p_name in SWISSEPH_OBJECTS:
            try:
                res, _ = swe.calc_ut(jd, SWISSEPH_OBJECTS[p_name], swe.FLG_EQUATORIAL)
                return res[1]
            except Exception:
                return None
        return None

    # Обогащаем планеты Широтой (lat) и Склонением (decl)
    for p in planets_list:
        p_name = p["name"]
        if p_name in SWISSEPH_OBJECTS:
            try:
                swe_id = SWISSEPH_OBJECTS[p_name]
                res_ecl, _ = swe.calc_ut(julian_day, swe_id, 0)
                lat_val = res_ecl[1]
                
                if p_name in ["True_South_Lunar_Node", "Mean_South_Lunar_Node"]:
                    lat_val = -lat_val

                p["lat"] = round(lat_val, 4)
                
                res_eq, _ = swe.calc_ut(julian_day, swe_id, swe.FLG_EQUATORIAL)
                decl_val = res_eq[1]

                if p_name in ["True_South_Lunar_Node", "Mean_South_Lunar_Node"]:
                    decl_val = -decl_val
                    
                p["decl"] = round(decl_val, 4)
                
            except Exception as e:
                print(f"[ENGINE ERROR] Ошибка расчета координат для {p_name}: {e}")
                p["lat"] = 0.0
                p["decl"] = 0.0
        else:
            p["lat"] = None
            p["decl"] = None

    # Перебираем уникальные пары
    for i in range(len(planets_list)):
        for j in range(i + 1, len(planets_list)):
            p1 = planets_list[i]
            p2 = planets_list[j]
            
            # Игнорируем очевидные оппозиции осей
            if p1["name"] == "True_North_Lunar_Node" and p2["name"] == "True_South_Lunar_Node": continue
            if p1["name"] == "Ascendant" and p2["name"] == "Descendant": continue
            if p1["name"] == "Medium_Coeli" and p2["name"] == "Imum_Coeli": continue
            
            # Проверяем, является ли аспект строгим (между фиктивными точками/углами)
            is_strict = (p1["name"] in STRICT_POINTS) and (p2["name"] in STRICT_POINTS)
            
            # Аспекты по долготе
            diff = abs(p1["abs_pos"] - p2["abs_pos"])
            if diff > 180:
                diff = 360 - diff
                
            # Перебираем правила из констант
            for angle, (asp_name, orb_normal, orb_strict) in ASPECT_RULES.items():
                max_orb = orb_strict if is_strict else orb_normal
                orb = abs(diff - angle)
                if orb <= max_orb:
                    clean_aspects.append({
                        "p1": p1["name"],
                        "p2": p2["name"],
                        "type": asp_name,
                        "orb": round(orb, 4),
                        "is_applying": False 
                    })
            
            # Аспекты по склонению (Параллели)
            if not is_strict:
                decl1 = get_declination(p1["name"], julian_day)
                decl2 = get_declination(p2["name"], julian_day)
                
                if decl1 is not None and decl2 is not None:
                    diff_decl = abs(abs(decl1) - abs(decl2))
                    if diff_decl <= 1.2: 
                        is_same_sign = (decl1 * decl2) > 0
                        asp_type = "parallel" if is_same_sign else "contraparallel"
                        clean_aspects.append({
                            "p1": p1["name"],
                            "p2": p2["name"],
                            "type": asp_type,
                            "orb": round(diff_decl, 4),
                            "is_applying": False
                        })
                        
    return clean_aspects