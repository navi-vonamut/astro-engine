# planet_status.py

def calculate_planet_status(aspects_list):
    """
    Рассчитывает индекс Гармоничности (зеленый) и Пораженности (красный) для ВСЕХ объектов карты.
    """
    malefics = ['Mars', 'Saturn', 'Uranus', 'Neptune', 'Pluto']
    benefics = ['Venus', 'Jupiter']
    
    status_data = {}
    
    # 1. Собираем все уникальные объекты, которые вступали в аспекты
    for a in aspects_list:
        for p in [a.get("p1"), a.get("p2")]:
            if p and p not in status_data:
                status_data[p] = {"harmony": 0, "tension": 0, "total": 0, "harmony_pct": 0, "tension_pct": 0}
                
    # 2. Начисляем баллы
    for a in aspects_list:
        p1 = a.get("p1")
        p2 = a.get("p2")
        a_type = a.get("type")
        orb = a.get("orb", 99)
        
        if not p1 or not p2:
            continue
            
        def add_scores(target, other, aspect, aspect_orb):
            harm = 0
            tens = 0
            
            if aspect == 'trine':
                harm += 3
            elif aspect == 'sextile':
                harm += 2
            elif aspect in ['square', 'opposition']:
                tens += 3
            elif aspect == 'conjunction':
                if other == 'Sun' and aspect_orb <= 8.5:
                    tens += 3  # Сожжение
                elif other in malefics:
                    tens += 2  # Соединение со "злой"
                elif other in benefics:
                    harm += 2  # Соединение с "доброй"
                else:
                    harm += 1  # Нейтральное соединение
            
            status_data[target]["harmony"] += harm
            status_data[target]["tension"] += tens

        # Аспект работает в обе стороны
        add_scores(p1, p2, a_type, orb)
        add_scores(p2, p1, a_type, orb)
        
    # 3. Считаем проценты
    for p, data in status_data.items():
        h = data["harmony"]
        t = data["tension"]
        total = h + t
        
        data["total"] = total
        if total > 0:
            data["harmony_pct"] = round((h / total) * 100)
            data["tension_pct"] = round((t / total) * 100)
            
    return status_data