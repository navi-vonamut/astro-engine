from typing import List, Dict, Any, Tuple

def get_compensatory_data(planets: List[Dict[str, Any]], aspects: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Анализирует карту и вытаскивает ключевые точки для компенсаторики:
    - Угловые планеты (локомотивы событий)
    - Самый точный напряженный аспект (главная боль и точка роста)
    - Самый точный гармоничный аспект (главный талант и опора)
    """
    
    # 1. Ищем угловые планеты (в 1, 4, 7 и 10 домах)
    angular_houses = {1, 4, 7, 10}
    angular_planets = []
    
    # Исключаем фиктивные точки из списка "локомотивов", фокусируемся на реальных энергиях
    real_planets = {"Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"}
    
    for p in planets:
        if p["name"] in real_planets and p.get("house") in angular_houses:
            angular_planets.append({
                "planet": p["name"],
                "house": p["house"],
                "sign": p["sign"]
            })
            
    # 2. Сортируем аспекты по точности (по возрастанию орбиса)
    # Фильтруем только аспекты между реальными планетами (чтобы не прорабатывать секстиль к Вертексу)
    valid_aspects = []
    for asp in aspects:
        if asp["p1"] in real_planets and asp["p2"] in real_planets:
            valid_aspects.append(asp)
            
    # Сортируем: чем меньше орбис, тем точнее аспект
    valid_aspects.sort(key=lambda x: x["orb"])
    
    # 3. Ищем ТОП аспекты
    tense_types = {"square", "opposition"}
    harmonic_types = {"trine", "sextile"}
    
    top_tense = None
    top_harmonic = None
    
    for asp in valid_aspects:
        # Находим первый (самый точный) напряженный
        if top_tense is None and asp["type"] in tense_types:
            top_tense = asp
            
        # Находим первый (самый точный) гармоничный
        if top_harmonic is None and asp["type"] in harmonic_types:
            top_harmonic = asp
            
        # Если оба нашли — прерываем цикл
        if top_tense and top_harmonic:
            break
            
    return {
        "angular_planets": angular_planets,
        "top_challenge_aspect": top_tense,  # Главный вызов
        "top_support_aspect": top_harmonic  # Главная опора
    }