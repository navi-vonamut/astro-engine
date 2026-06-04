from typing import List, Dict, Any

def calculate_synastry_indices(aspects: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Математический скоринг синастрии для ИИ и фронтенда.
    Анализирует межкарточные аспекты и собирает индексы по психологическим блокам.
    """
    conflict_planets = {"Mars", "Saturn", "Pluto"}
    passion_planets = {"Sun", "Moon", "Venus", "Mars"}
    mental_planets = {"Mercury", "Sun", "Uranus"}
    
    scores = {
        "conflict_index": 0,      # Уровень трения, кризисов и уроков
        "love_passion_index": 0,   # Сексуальный, романтический клей и притяжение
        "mental_index": 0,        # Ментальный коннект, понимание и общение
        "support_index": 0         # Взаимовыручка, стабильность и долговечность
    }
    
    for a in aspects:
        # Приводим к единому стандарту ключи (в синастрии это person1_object и person2_object)
        p1 = a.get("person1_object")
        p2 = a.get("person2_object")
        asp_type = a.get("aspect", "").lower()
        orb = a.get("orb", 1.0)
        
        if not p1 or not p2 or not asp_type:
            continue
            
        # Сила аспекта зависит от орбиса (чем точнее, тем выше балл)
        weight = max(0.5, 3.0 - (orb / 2.0))
        
        # 1. БЛОК КОНФЛИКТНОСТИ (Взаимодействие вредителей)
        if p1 in conflict_planets and p2 in conflict_planets:
            if asp_type in ["conjunction", "square", "opposition"]:
                scores["conflict_index"] += int(4 * weight)
            elif asp_type in ["trine", "sextile"]:
                scores["conflict_index"] -= int(1 * weight)
                
        # 2. БЛОК ЛЮБВИ И СТРАСТИ
        if p1 in passion_planets and p2 in passion_planets:
            # Классические маркеры притяжения: Венера-Марс, Солнце-Луна, Венера-Венера, Луна-Венера
            pair = {p1, p2}
            if pair in [{"Venus", "Mars"}, {"Sun", "Moon"}, {"Venus", "Venus"}, {"Moon", "Venus"}]:
                if asp_type in ["conjunction", "trine", "sextile"]:
                    scores["love_passion_index"] += int(5 * weight)
                elif asp_type in ["square", "opposition"]:
                    # В синастрии напряжение Венера-Марс дает штормовую страсть, заносим в плюс блоку
                    scores["love_passion_index"] += int(3 * weight) 
                    
        # 3. МЕНТАЛЬНЫЙ БЛОК (Интеллектуальная волна)
        if p1 in mental_planets or p2 in mental_planets:
            if "Mercury" in {p1, p2}:
                if asp_type in ["conjunction", "trine", "sextile"]:
                    scores["mental_index"] += int(3 * weight)
                elif asp_type in ["square", "opposition"]:
                    scores["mental_index"] -= int(1 * weight)

        # 4. БЛОК СТАБИЛЬНОСТИ И ПОДДЕРЖКИ (Юпитер и Сатурн)
        if "Jupiter" in {p1, p2} and asp_type in ["conjunction", "trine", "sextile"]:
            scores["support_index"] += int(3 * weight)  # Благословение союза
        if "Saturn" in {p1, p2} and asp_type in ["conjunction", "trine", "sextile"]:
            scores["support_index"] += int(2 * weight)  # Сатурн скрепляет обязательствами

    # Страховка от отрицательных значений при вычитании
    for k in scores:
        if scores[k] < 0: 
            scores[k] = 0

    return {
        "scoring": scores,
        "summary_verdict": "high_conflict" if scores["conflict_index"] > 15 else "harmonious"
    }