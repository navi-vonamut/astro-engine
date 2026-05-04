from app.engine.core.constants import JONES_PATTERN_NAMES # 🔥 Импортируем константы

def calculate_jones_pattern(planets_data):
    """Анализирует список планет и возвращает Фигуру Джонса."""
    main_ids = {"sun", "moon", "mercury", "venus", "mars", 
                "jupiter", "saturn", "uranus", "neptune", "pluto"}
    
    main_planets = [p for p in planets_data if p.get("id", p.get("name", "").lower()) in main_ids]
    if len(main_planets) < 10: return None

    sorted_planets = sorted(main_planets, key=lambda x: x["abs_pos"])
    
    gaps = []
    for i in range(10):
        p1 = sorted_planets[i]
        p2 = sorted_planets[(i + 1) % 10]
        gap_size = (p2["abs_pos"] - p1["abs_pos"]) % 360
        gaps.append({"size": gap_size, "p1": p1, "p2": p2})
        
    gaps.sort(key=lambda x: x["size"], reverse=True)
    g1, g2, g3 = gaps[0], gaps[1], gaps[2]
    
    # По умолчанию Брызги
    pattern_id = "splash"
    focus_planet = None
    
    # Корзина
    shared_planet = None
    if g1["p1"] == g2["p2"]: shared_planet = g1["p1"]
    elif g1["p2"] == g2["p1"]: shared_planet = g1["p2"]
    
    if shared_planet and (g1["size"] + g2["size"] >= 150) and g1["size"] >= 60 and g2["size"] >= 60:
        pattern_id = "bucket"
        focus_planet = shared_planet["name"]
        
    # Качели
    elif g1["size"] >= 60 and g2["size"] >= 60 and not shared_planet:
        pattern_id = "seesaw"
    
    # Связка
    elif g1["size"] >= 240:
        pattern_id = "bundle"
        focus_planet = g1["p2"]["name"] 
        
    # Чаша
    elif 170 <= g1["size"] < 240:
        pattern_id = "bowl"
        focus_planet = g1["p2"]["name"]
        
    # Локомотив
    elif 110 <= g1["size"] < 170:
        pattern_id = "locomotive"
        focus_planet = g1["p2"]["name"]
        
    # Праща
    elif g3["size"] >= 60:
        pattern_id = "splay"
        
    return {
        "id": pattern_id,
        "name": JONES_PATTERN_NAMES.get(pattern_id, "Splash"), # Берем имя из константы
        "focus_planet": focus_planet,
        "empty_start": g1["p1"]["abs_pos"], 
        "empty_end": g1["p2"]["abs_pos"]    
    }