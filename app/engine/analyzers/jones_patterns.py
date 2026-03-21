# jones_patterns.py

def calculate_jones_pattern(planets_data):
    """
    Анализирует список планет и возвращает Фигуру Джонса.
    """
    # 1. Берем только 10 классических планет (без узлов, фиктивных точек и астероидов)
    main_ids = {"sun", "moon", "mercury", "venus", "mars", 
                "jupiter", "saturn", "uranus", "neptune", "pluto"}
    
    # Ищем планеты в данных по 'id' или 'name' (в нижнем регистре)
    main_planets = [p for p in planets_data if p.get("id", p.get("name", "").lower()) in main_ids]
    
    if len(main_planets) < 10:
        return None

    # 2. Сортируем по абсолютному градусу (от 0 до 360) - ИСПРАВЛЕНО НА abs_pos
    sorted_planets = sorted(main_planets, key=lambda x: x["abs_pos"])
    
    # 3. Вычисляем расстояния (пустоты) между соседними планетами
    gaps = []
    for i in range(10):
        p1 = sorted_planets[i]
        p2 = sorted_planets[(i + 1) % 10]
        # Дистанция вперед по зодиаку от p1 до p2
        gap_size = (p2["abs_pos"] - p1["abs_pos"]) % 360
        gaps.append({"size": gap_size, "p1": p1, "p2": p2})
        
    # Сортируем пустоты по убыванию
    gaps.sort(key=lambda x: x["size"], reverse=True)
    g1, g2, g3 = gaps[0], gaps[1], gaps[2]
    
    pattern_id = "splash"
    pattern_name = "Брызги"
    focus_planet = None
    
    # 4. Логика определения фигуры
    
    # Проверяем Корзину (Bucket): 
    # Две самые большие пустоты стоят рядом и отделяют ровно 1 планету-ручку
    shared_planet = None
    if g1["p1"] == g2["p2"]: shared_planet = g1["p1"]
    elif g1["p2"] == g2["p1"]: shared_planet = g1["p2"]
    
    if shared_planet and (g1["size"] + g2["size"] >= 150) and g1["size"] >= 60 and g2["size"] >= 60:
        pattern_id = "bucket"
        pattern_name = "Корзина"
        focus_planet = shared_planet["name"]
        
    # Проверяем Качели (See-Saw):
    elif g1["size"] >= 60 and g2["size"] >= 60 and not shared_planet:
        pattern_id = "seesaw"
        pattern_name = "Качели"
    
    # Проверяем остальные фигуры по самой большой пустоте (g1)
    elif g1["size"] >= 240:
        pattern_id = "bundle"
        pattern_name = "Связка"
        focus_planet = g1["p2"]["name"] # Ведущая планета (первая после пустоты)
        
    elif 170 <= g1["size"] < 240:
        pattern_id = "bowl"
        pattern_name = "Чаша"
        focus_planet = g1["p2"]["name"]
        
    elif 110 <= g1["size"] < 170:
        pattern_id = "locomotive"
        pattern_name = "Локомотив"
        focus_planet = g1["p2"]["name"]
        
    elif g3["size"] >= 60:
        pattern_id = "splay"
        pattern_name = "Праща"
        
    return {
        "id": pattern_id,
        "name": pattern_name,
        "focus_planet": focus_planet,
        "empty_start": g1["p1"]["abs_pos"], # ИСПРАВЛЕНО НА abs_pos
        "empty_end": g1["p2"]["abs_pos"]    # ИСПРАВЛЕНО НА abs_pos
    }