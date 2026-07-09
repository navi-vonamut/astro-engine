# app/engine/calculators/firdaria_calc.py
from datetime import datetime

# Периоды планет в годах
FIRDARIA_YEARS = {
    "Sun": 10.0,
    "Venus": 8.0,
    "Mercury": 13.0,
    "Moon": 9.0,
    "Saturn": 11.0,
    "Jupiter": 12.0,
    "Mars": 7.0,
    "True_North_Lunar_Node": 3.0,
    "Mean_North_Lunar_Node": 3.0,
    "True_South_Lunar_Node": 2.0,
    "Mean_South_Lunar_Node": 2.0
}

# Последовательности для дневной и ночной карт (Узлы идут в конце)
DAY_SEQ = ["Sun", "Venus", "Mercury", "Moon", "Saturn", "Jupiter", "Mars", "True_North_Lunar_Node", "True_South_Lunar_Node"]
NIGHT_SEQ = ["Moon", "Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "True_North_Lunar_Node", "True_South_Lunar_Node"]

def calculate_firdaria(birth_date_str: str, target_date_str: str, is_day_chart: bool) -> dict:
    """
    Рассчитывает текущий большой период (Major) и подпериод (Minor) Фирдара.
    """
    b_date = datetime.strptime(birth_date_str, "%Y-%m-%d")
    t_date = datetime.strptime(target_date_str, "%Y-%m-%d")
    
    # Точный возраст в годах
    age_days = (t_date - b_date).days
    age_years = age_days / 365.25
    
    # Фирдары циклично повторяются каждые 75 лет
    current_cycle_age = age_years % 75.0
    
    sequence = DAY_SEQ if is_day_chart else NIGHT_SEQ
    
    major_planet = "Sun"
    accumulated_years = 0.0
    major_duration = 10.0
    
    # 1. Ищем текущий Большой период
    for planet in sequence:
        period_len = FIRDARIA_YEARS.get(planet, 0)
        if current_cycle_age < accumulated_years + period_len:
            major_planet = planet
            major_duration = period_len
            break
        accumulated_years += period_len
        
    # 2. Ищем Подпериод (Minor)
    # Узлы традиционно не делятся на подпериоды, возвращаем их же
    if "Node" in major_planet:
        minor_planet = major_planet
    else:
        # В Большом периоде 7 подпериодов. Подпериод равен 1/7 от большого.
        # Цикл подпериодов начинается с хозяина Большого периода и идет по той же последовательности
        minor_duration = major_duration / 7.0
        years_into_major = current_cycle_age - accumulated_years
        minor_index_offset = int(years_into_major // minor_duration)
        
        # Получаем только 7 главных планет из последовательности
        sub_sequence = [p for p in sequence if "Node" not in p]
        start_idx = sub_sequence.index(major_planet)
        
        minor_idx = (start_idx + minor_index_offset) % 7
        minor_planet = sub_sequence[minor_idx]
        
    return {
        "major_planet": major_planet,
        "minor_planet": minor_planet,
        "cycle_age": round(current_cycle_age, 2)
    }