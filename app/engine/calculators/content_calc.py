import swisseph as swe
import datetime
from typing import Dict, List, Any
from app.engine.core.constants import SIGNS_SHORT, SWISSEPH_OBJECTS

# Маппинг знаков в их порядковый номер (0-11)
SIGN_TO_ID = {sign: i for i, sign in enumerate(SIGNS_SHORT)}

def get_solar_house(planet_sign_id: int, target_sign_id: int) -> int:
    """
    Рассчитывает номер дома по системе Солнечных знаков (Whole Sign).
    Пример: Если мы смотрим для Тельца (1), а планета в Раке (3).
    (3 - 1) % 12 + 1 = 3-й дом.
    """
    return ((planet_sign_id - target_sign_id) % 12) + 1

def generate_content_events(target_sign: str, start_date: str, end_date: str) -> Dict[str, Any]:
    """Сканирует период и собирает астро-события для конкретного знака зодиака"""
    target_sign_id = SIGN_TO_ID.get(target_sign.capitalize()[:3], 0)
    
    start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d")
    delta_days = (end_dt - start_dt).days
    
    # Защита от слишком долгих сканирований (макс 2 года)
    delta_days = min(delta_days, 730) 

    # Планеты, которые важны для контента
    PLANETS = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]
    
    events = []
    start_positions = []
    prev_state = {}
    
    for day_offset in range(delta_days + 1):
        curr_dt = start_dt + datetime.timedelta(days=day_offset)
        # Считаем на полдень (универсально)
        jd = swe.julday(curr_dt.year, curr_dt.month, curr_dt.day, 12.0)
        
        for p_name in PLANETS:
            pid = SWISSEPH_OBJECTS.get(p_name)
            if pid is None: continue
                
            res = swe.calc_ut(jd, pid, swe.FLG_SWIEPH | swe.FLG_SPEED)
            lon = res[0][0]
            speed = res[0][3]
            
            sign_id = int(lon // 30)
            is_retro = speed < 0
            solar_house = get_solar_house(sign_id, target_sign_id)
            
            # Если это первый день (start_date) - записываем стартовые позиции
            if day_offset == 0:
                start_positions.append({
                    "planet": p_name,
                    "sign": SIGNS_SHORT[sign_id],
                    "solar_house": solar_house,
                    "is_retro": is_retro
                })
                prev_state[p_name] = {"sign_id": sign_id, "is_retro": is_retro}
                continue
            
            # --- ПОИСК СОБЫТИЙ (Ингрессии и Ретроградность) ---
            
            # 1. Смена Знака/Дома (Ингрессия)
            if prev_state[p_name]["sign_id"] != sign_id:
                events.append({
                    "date": curr_dt.strftime("%Y-%m-%d"),
                    "planet": p_name,
                    "event_type": "ingress",
                    "from_sign": SIGNS_SHORT[prev_state[p_name]["sign_id"]],
                    "to_sign": SIGNS_SHORT[sign_id],
                    "to_solar_house": solar_house
                })
                
            # 2. Смена направления (Стационарность -> Разворот)
            # Луна и Солнце не бывают ретроградными, их пропускаем
            if p_name not in ["Sun", "Moon"]:
                if prev_state[p_name]["is_retro"] != is_retro:
                    direction = "retrograde" if is_retro else "direct"
                    events.append({
                        "date": curr_dt.strftime("%Y-%m-%d"),
                        "planet": p_name,
                        "event_type": "station",
                        "direction": direction,
                        "in_solar_house": solar_house,
                        "in_sign": SIGNS_SHORT[sign_id]
                    })
                
            # Обновляем стейт на следующий день
            prev_state[p_name] = {"sign_id": sign_id, "is_retro": is_retro}
            
    return {
        "meta": {
            "target_sign": target_sign.capitalize()[:3],
            "start_date": start_date,
            "end_date": end_date
        },
        "start_positions": start_positions,
        "events": events
    }