# aspect_patterns.py
import itertools

def calculate_aspect_patterns(aspects_list):
    """
    Ищет замкнутые фигуры аспектов (Тау-квадрат, Большой тригон, Парус, Йод и т.д.).
    """
    # 1. Строим словарь для быстрого поиска аспекта между двумя планетами
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

# Работаем со ВСЕМИ объектами, которые образовали аспекты (Планеты, Узлы, Хирон, Лилит, Астероиды)
    # Исключаем только Углы карты (ASC, MC, DSC, IC), так как это математические оси, а не тела
    excluded_points = ["Ascendant", "Medium_Coeli", "Descendant", "Imum_Coeli"]
    active_planets = [p for p in aspect_map.keys() if p not in excluded_points]
    
    patterns = []
    
    # === ФИГУРЫ ИЗ 3 ПЛАНЕТ ===
    for combo in itertools.combinations(active_planets, 3):
        p1, p2, p3 = combo
        edges = [get_aspect(p1, p2), get_aspect(p1, p3), get_aspect(p2, p3)]
        
        # 1. Тау-квадрат (1 оппозиция, 2 квадрата)
        if edges.count('opposition') == 1 and edges.count('square') == 2:
            # Ищем вершину (ту планету, которая не участвует в оппозиции)
            apex = p3 if get_aspect(p1, p2) == 'opposition' else p2 if get_aspect(p1, p3) == 'opposition' else p1
            patterns.append({
                "name": "Тау-квадрат", "type": "t_square", "planets": list(combo), "apex": apex,
                "desc": "Мощный источник напряжения и жизненной динамики. Проблема (оппозиция) требует решения через действие по фокусной планете."
            })
            
        # 2. Большой тригон (3 трина)
        elif edges.count('trine') == 3:
            patterns.append({
                "name": "Большой тригон", "type": "grand_trine", "planets": list(combo), "apex": None,
                "desc": "Врожденный талант, удача и защита. Энергия течет так легко, что может давать лень, если нет напряженных аспектов."
            })
            
        # 3. Перст судьбы / Йод (1 секстиль, 2 квинконса)
        elif edges.count('quincunx') == 2 and edges.count('sextile') == 1:
            apex = p3 if get_aspect(p1, p2) == 'sextile' else p2 if get_aspect(p1, p3) == 'sextile' else p1
            patterns.append({
                "name": "Перст судьбы (Йод)", "type": "yod", "planets": list(combo), "apex": apex,
                "desc": "Специфическая кармическая задача. Ощущение, что человека ведут невидимые силы к цели, символизируемой вершиной."
            })

    # === ФИГУРЫ ИЗ 4 ПЛАНЕТ ===
    for combo in itertools.combinations(active_planets, 4):
        p1, p2, p3, p4 = combo
        edges = [
            get_aspect(p1, p2), get_aspect(p1, p3), get_aspect(p1, p4),
            get_aspect(p2, p3), get_aspect(p2, p4), get_aspect(p3, p4)
        ]
        
        # 4. Большой крест (2 оппозиции, 4 квадрата)
        if edges.count('opposition') == 2 and edges.count('square') == 4:
            patterns.append({
                "name": "Большой крест", "type": "grand_cross", "planets": list(combo), "apex": None,
                "desc": "Невероятное напряжение. Человек словно распят на кресте обстоятельств, но это дает огромную пробивную силу."
            })
            
        # 5. Мистический прямоугольник (2 оппозиции, 2 трина, 2 секстиля)
        elif edges.count('opposition') == 2 and edges.count('trine') == 2 and edges.count('sextile') == 2:
            patterns.append({
                "name": "Мистический прямоугольник", "type": "mystic_rectangle", "planets": list(combo), "apex": None,
                "desc": "Умение находить гармонию в конфликтах. Внутреннее напряжение легко переводится в практический результат."
            })
            
        # 6. Парус / Змей (3 трина, 1 оппозиция, 2 секстиля)
        elif edges.count('trine') == 3 and edges.count('opposition') == 1 and edges.count('sextile') == 2:
            # Вершина Паруса — это та планета, которая делает два секстиля
            apex = None
            for p in combo:
                p_edges = [get_aspect(p, other) for other in combo if other != p]
                if p_edges.count('sextile') == 2:
                    apex = p
            patterns.append({
                "name": "Парус (Змей)", "type": "kite", "planets": list(combo), "apex": apex,
                "desc": "Удачная конфигурация. Большой тригон дает таланты, а оппозиция дает мачту и вектор движения для их реализации."
            })

    # Сортируем: сначала крупные фигуры (4 планеты), потом мелкие
    patterns.sort(key=lambda x: len(x["planets"]), reverse=True)
    
    return patterns