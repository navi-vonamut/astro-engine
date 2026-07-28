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

def calculate_electional_score(
    category: str,
    retrograde_planets: List[str],
    is_waxing: bool,
    moon_in_via_combusta: bool,
    aspects: List[Dict[str, Any]]
) -> int:
    """Расчет скоринга качества дня (15 - 99) под конкретную категорию"""
    score = 70.0
    cat = (category or "business").lower()

    is_mercury_retro = "Mercury" in retrograde_planets
    is_venus_retro = "Venus" in retrograde_planets
    is_mars_retro = "Mars" in retrograde_planets

    harmonious_types = {"Trine", "Sextile", "trine", "sextile", "Conjunction", "conjunction"}
    tense_types = {"Square", "Opposition", "square", "opposition"}

    if cat == "business":
        if is_mercury_retro: score -= 30.0
        if is_mars_retro: score -= 20.0
        if is_waxing: score += 10.0

        for a in aspects:
            p1 = a.get("planet1") or a.get("p1")
            p2 = a.get("planet2") or a.get("p2")
            t = a.get("type") or a.get("aspect")
            pair = {p1, p2}
            if pair & {"Mercury", "Jupiter", "Sun", "Mars"}:
                if t in harmonious_types: score += 4.0
                elif t in tense_types: score -= 6.0

    elif cat == "wedding":
        if is_venus_retro: score -= 35.0
        if is_mars_retro: score -= 15.0
        if moon_in_via_combusta: score -= 20.0
        if is_waxing: score += 8.0

        for a in aspects:
            p1 = a.get("planet1") or a.get("p1")
            p2 = a.get("planet2") or a.get("p2")
            t = a.get("type") or a.get("aspect")
            pair = {p1, p2}
            if pair & {"Venus", "Moon", "Sun"}:
                if t in harmonious_types: score += 5.0
                elif t in tense_types: score -= 8.0

    elif cat == "relocation":
        if moon_in_via_combusta: score -= 25.0
        if is_mercury_retro: score -= 15.0
        if is_waxing: score += 8.0

        for a in aspects:
            p1 = a.get("planet1") or a.get("p1")
            p2 = a.get("planet2") or a.get("p2")
            t = a.get("type") or a.get("aspect")
            pair = {p1, p2}
            if pair & {"Moon", "Jupiter", "Mercury"}:
                if t in harmonious_types: score += 5.0
                elif t in tense_types: score -= 6.0

    elif cat == "health":
        if is_waxing: score += 15.0
        if is_mars_retro: score -= 15.0

        for a in aspects:
            p1 = a.get("planet1") or a.get("p1")
            p2 = a.get("planet2") or a.get("p2")
            t = a.get("type") or a.get("aspect")
            pair = {p1, p2}
            if pair & {"Sun", "Moon", "Jupiter"}:
                if t in harmonious_types: score += 5.0
                elif t in tense_types: score -= 7.0

    elif cat == "launch":
        if is_mercury_retro: score -= 25.0
        if is_mars_retro: score -= 20.0
        if is_waxing: score += 12.0

        for a in aspects:
            p1 = a.get("planet1") or a.get("p1")
            p2 = a.get("planet2") or a.get("p2")
            t = a.get("type") or a.get("aspect")
            pair = {p1, p2}
            if pair & {"Mars", "Uranus", "Jupiter", "Sun"}:
                if t in harmonious_types: score += 5.0
                elif t in tense_types: score -= 7.0

    elif cat == "purchase":
        if is_mercury_retro: score -= 30.0
        if is_venus_retro: score -= 20.0

        for a in aspects:
            p1 = a.get("planet1") or a.get("p1")
            p2 = a.get("planet2") or a.get("p2")
            t = a.get("type") or a.get("aspect")
            pair = {p1, p2}
            if pair & {"Venus", "Mercury", "Saturn"}:
                if t in harmonious_types: score += 5.0
                elif t in tense_types: score -= 6.0

    else:
        if is_mercury_retro: score -= 15.0
        if is_waxing: score += 5.0

    return max(15, min(99, int(round(score))))

def analyze_electional_day(chart: Dict[str, Any], category: str = "business") -> Dict[str, Any]:
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

    # 4. Фильтруем аспекты: строгий орбис <= 3.5° и только ключевые планеты
    MAIN_PLANET_NAMES = {
        "Sun", "Moon", "Mercury", "Venus", "Mars",
        "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto",
        "True_North_Lunar_Node", "Chiron"
    }

    raw_aspects = chart.get("aspects", [])
    filtered_aspects = []
    for a in raw_aspects:
        p1 = a.get("planet1") or a.get("p1")
        p2 = a.get("planet2") or a.get("p2")
        orb = abs(float(a.get("orb", 0)))

        if p1 in MAIN_PLANET_NAMES and p2 in MAIN_PLANET_NAMES and orb <= 3.5:
            filtered_aspects.append(a)

    # 5. Категориальный скоринг дня
    score = calculate_electional_score(
        category=category,
        retrograde_planets=retrograde_planets,
        is_waxing=is_waxing,
        moon_in_via_combusta=moon_in_via_combusta,
        aspects=filtered_aspects
    )

    return {
        "date": chart["meta"]["datetime"].split("T")[0],
        "moon_sign": moon_sign,
        "moon_is_waxing": is_waxing,
        "moon_in_via_combusta": moon_in_via_combusta,
        "retrograde_planets": retrograde_planets,
        "is_mercury_retro": "Mercury" in retrograde_planets,
        "is_venus_retro": "Venus" in retrograde_planets,
        "score": score,
        "quality_score": score,
        "planets": chart.get("planets", []),
        "houses": chart.get("houses", []),
        "aspects": filtered_aspects,
        "chart": chart
    }