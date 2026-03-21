# dominants.py

def calculate_dominants(planets_list, houses_list, aspects_list):
    """
    Рассчитывает силу (афетику) 10 мажорных планет в карте по правилам Astro-Seek.
    """
    main_planets = ['Sun', 'Moon', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn', 'Uranus', 'Neptune', 'Pluto']
    
    # === 1. МАТРИЦА ДОСТОИНСТВ В ЗНАКАХ (0 - 6 баллов) ===
    def get_sign_score(planet, sign):
        if not sign: return 3
        s = sign.lower()[:3] # Берем первые 3 буквы (ari, tau, gem...)
        
        # 6=Обитель, 5=Экзальтация, 4=Дружба, 3=Нейтралитет, 2=Вражда, 1=Падение, 0=Изгнание
        scores = {
            'Sun': {'leo':6, 'ari':5, 'sag':4, 'gem':3, 'vir':3, 'pis':3, 'tau':2, 'can':2, 'sco':2, 'cap':2, 'lib':1, 'aqu':0},
            'Moon': {'can':6, 'tau':5, 'pis':4, 'vir':4, 'gem':3, 'lib':3, 'aqu':3, 'ari':2, 'leo':2, 'sag':2, 'sco':1, 'cap':0},
            'Mercury': {'gem':6, 'vir':6, 'aqu':5, 'lib':4, 'tau':4, 'cap':4, 'ari':3, 'leo':3, 'sco':3, 'can':2, 'pis':1, 'sag':0},
            'Venus': {'tau':6, 'lib':6, 'pis':5, 'gem':4, 'aqu':4, 'cap':4, 'can':3, 'leo':3, 'sag':3, 'sco':0, 'ari':0, 'vir':1},
            'Mars': {'ari':6, 'sco':6, 'cap':5, 'leo':4, 'sag':4, 'pis':4, 'gem':3, 'vir':3, 'aqu':3, 'tau':0, 'lib':0, 'can':1},
            'Jupiter': {'sag':6, 'pis':6, 'can':5, 'ari':4, 'leo':4, 'sco':4, 'tau':3, 'lib':3, 'aqu':3, 'gem':0, 'vir':0, 'cap':1},
            'Saturn': {'cap':6, 'aqu':6, 'lib':5, 'tau':4, 'vir':4, 'gem':4, 'sag':3, 'pis':3, 'sco':2, 'ari':1, 'can':0, 'leo':0},
            'Uranus': {'aqu':6, 'sco':5, 'gem':4, 'lib':4, 'sag':3, 'pis':3, 'ari':3, 'vir':2, 'cap':2, 'can':2, 'tau':1, 'leo':0},
            'Neptune': {'pis':6, 'can':5, 'sco':4, 'tau':3, 'cap':3, 'ari':3, 'lib':2, 'gem':2, 'sag':2, 'aqu':1, 'vir':0, 'leo':1},
            'Pluto': {'sco':6, 'ari':5, 'pis':4, 'can':4, 'sag':3, 'aqu':3, 'tau':0, 'lib':1, 'gem':2, 'vir':2, 'cap':2, 'leo':2}
        }
        return scores.get(planet, {}).get(s, 3) # Если не найдено, отдаем нейтральные 3 балла

    # Функция управителей знаков
    def get_ruler(sign_name):
        if not sign_name: return ""
        s = str(sign_name).lower()
        if "ari" in s: return "Mars"
        if "tau" in s: return "Venus"
        if "gem" in s: return "Mercury"
        if "can" in s: return "Moon"
        if "leo" in s: return "Sun"
        if "vir" in s: return "Mercury"
        if "lib" in s: return "Venus"
        if "sco" in s: return "Pluto"     
        if "sag" in s: return "Jupiter"
        if "cap" in s: return "Saturn"
        if "aqu" in s: return "Uranus"    
        if "pis" in s: return "Neptune"   
        return ""

    # Символические управители домов
    symbolic_houses = {
        'Mars': [1], 'Venus': [2, 7], 'Mercury': [3, 6], 'Moon': [4], 'Sun': [5], 
        'Pluto': [8], 'Jupiter': [9], 'Saturn': [10], 'Uranus': [11], 'Neptune': [12]
    }

    # === СОБИРАЕМ БАЛЛЫ ЗА УПРАВЛЕНИЕ (Из прошлого шага, формула подтверждена) ===
    rule_pts_dict = {p: 0 for p in main_planets}
    for p in planets_list:
        p_name = p.get("name")
        if p_name in main_planets:
            ruler = get_ruler(p.get("sign", ""))
            if ruler in rule_pts_dict:
                rule_pts_dict[ruler] += 1  

    asc_sign = next((h.get("sign", "") for h in houses_list if h.get("house") == 1), "")
    mc_sign = next((h.get("sign", "") for h in houses_list if h.get("house") == 10), "")
    
    asc_ruler = get_ruler(asc_sign)
    if asc_ruler in rule_pts_dict: rule_pts_dict[asc_ruler] += 3
        
    mc_ruler = get_ruler(mc_sign)
    if mc_ruler in rule_pts_dict: rule_pts_dict[mc_ruler] += 1

    # === ОСНОВНОЙ ЦИКЛ ПО ПЛАНЕТАМ ===
    dominants = []
    total_points = 0

    for p_name in main_planets:
        p = next((pl for pl in planets_list if pl.get("name") == p_name), None)
        if not p:
            continue
            
        # 1. ЗНАК (по новой матрице 0-6)
        sign_pts = get_sign_score(p_name, p.get("sign", ""))
        
        # 2. ДОМ
        house_pts = 0
        h_num = p.get("house")
        if h_num in [1, 10]: 
            house_pts += 1 # +1 если в 1 или 10 доме
        if h_num in symbolic_houses.get(p_name, []): 
            house_pts += 1 # +1 если в символическом доме (например Венера во 2-м)
            
        # 3. УГОЛ (Орбис строго <= 6.0)
        angle_pts = 0
        for a in aspects_list:
            if (a.get("p1") == p_name or a.get("p2") == p_name) and a.get("type") == "conjunction" and a.get("orb", 99) <= 6.0:
                other = a["p2"] if a["p1"] == p_name else a["p1"]
                if other in ["Ascendant", "Medium_Coeli"]:
                    angle_pts = max(angle_pts, 5) # ASC и MC дают +5
                elif other in ["Descendant", "Imum_Coeli"]:
                    angle_pts = max(angle_pts, 3) # DSC и IC дают +3
                    
        # 4. УПРАВЛЕНИЕ (Уже посчитали)
        rule_pts = rule_pts_dict.get(p_name, 0)
        
        # 5. АСПЕКТЫ (Считаем только мажорные аспекты с другими ПЛАНЕТАМИ, исключая узлы/фиктивные)
        aspect_pts = 0
        for a in aspects_list:
            p1, p2 = a.get("p1"), a.get("p2")
            if (p1 == p_name and p2 in main_planets) or (p2 == p_name and p1 in main_planets):
                a_type = a.get("type")
                if a_type in ['trine', 'sextile']: aspect_pts += 3
                elif a_type == 'conjunction': aspect_pts += 2
                elif a_type in ['square', 'opposition']: aspect_pts += 1
                    
        # ИТОГО
        sum_pts = sign_pts + house_pts + angle_pts + rule_pts + aspect_pts
        total_points += sum_pts
        
        dominants.append({
            "name": p_name,
            "signPts": sign_pts,
            "housePts": house_pts,
            "anglePts": angle_pts,
            "rulePts": rule_pts,
            "aspectPts": aspect_pts,
            "sum": sum_pts
        })
        
    # Рассчитываем проценты
    for d in dominants:
        d["percent"] = round((d["sum"] / total_points * 100), 2) if total_points > 0 else 0.0
        
    dominants.sort(key=lambda x: x["sum"], reverse=True)
    
    return dominants