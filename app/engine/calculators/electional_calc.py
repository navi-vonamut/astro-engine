import datetime
from typing import List, Dict, Any
from app.engine.core.models import BirthInput

def generate_daily_inputs(start_date: str, end_date: str, lat: float, lon: float, tz: str) -> List[BirthInput]:
    """Генерирует список входных данных на каждый день в заданном периоде (на полдень)"""
    inputs = []
    
    start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d")
    
    # Защита от слишком больших периодов (максимум 60 дней за один запрос)
    delta = min((end_dt - start_dt).days, 60)
    
    curr_dt = start_dt
    for _ in range(delta + 1):
        date_str = curr_dt.strftime("%Y-%m-%d")
        # Строим карту на 12:00 местного времени — это стандарт для дневной оценки
        inp = BirthInput(
            name=f"Electional {date_str}",
            date=date_str,
            time="12:00:00",
            tz=tz,
            lat=lat,
            lon=lon
        )
        inputs.append(inp)
        curr_dt += datetime.timedelta(days=1)
        
    return inputs

def analyze_electional_day(chart: Dict[str, Any]) -> Dict[str, Any]:
    """Анализирует карту дня и вытаскивает ключевые маркеры для планирования"""
    planets = {p["name"]: p for p in chart["planets"]}
    
    # 1. Проверяем ретроградность (Критично для электива!)
    retrograde_planets = [name for name, p in planets.items() if p.get("is_retro")]
    
    # 2. Оцениваем Луну (Самая важная планета в подборе дат)
    moon = planets.get("Moon", {})
    sun = planets.get("Sun", {})
    
    moon_sign = moon.get("sign", "")
    
    # Фаза Луны: Угол между Луной и Солнцем
    moon_phase_angle = (moon.get("abs_pos", 0) - sun.get("abs_pos", 0)) % 360
    is_waxing = moon_phase_angle < 180 # Растущая (хорошо для старта)
    
    # 3. Сожженный путь (Via Combusta)
    moon_in_via_combusta = 195.0 <= moon.get("abs_pos", 0) <= 225.0
    
    return {
        "date": chart["meta"]["datetime"].split("T")[0],
        "moon_sign": moon_sign,
        "moon_is_waxing": is_waxing,
        "moon_in_via_combusta": moon_in_via_combusta,
        "retrograde_planets": retrograde_planets,
        # Если Меркурий или Венера ретроградны - день плох для бизнеса/свадьбы
        "is_mercury_retro": "Mercury" in retrograde_planets,
        "is_venus_retro": "Venus" in retrograde_planets,
    }