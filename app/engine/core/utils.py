import re
import time
from datetime import datetime
import pytz
import swisseph as swe

# Регулярка для парсинга часовых поясов вида +03:00
_OFFSET_RE = re.compile(r"^([+-])(\d{2}):?(\d{2})$")

def norm_date(s: str) -> str:
    """Приводит дату к стандарту YYYY-MM-DD"""
    s = (s or "").strip().replace("/", "-")
    return s

def tz_to_pytz(tz: str) -> str:
    """Конвертирует строковый таймзону (например, +03:00) в формат pytz (Etc/GMT-3)"""
    tz = (tz or "").strip()
    if not tz: return "UTC"
    if "/" in tz and not tz.startswith(("+", "-")): return tz
    m = _OFFSET_RE.match(tz)
    if not m: return "UTC"
    sign, hh, mm = m.group(1), int(m.group(2)), int(m.group(3))
    if mm != 0: return "UTC"
    if sign == "+": return f"Etc/GMT-{hh}"
    return f"Etc/GMT+{hh}"

def parse_ymd(date_str: str) -> tuple[int, int, int]:
    """Разбивает строку даты на год, месяц и день"""
    d = norm_date(date_str)
    y, m, day = d.split("-")
    return int(y), int(m), int(day)

def parse_hm(time_str: str) -> tuple[int, int]:
    """Разбивает строку времени на часы и минуты"""
    t = (time_str or "").strip()
    parts = t.split(":")
    if len(parts) < 2: raise ValueError(f"Bad time format: {time_str}")
    return int(parts[0]), int(parts[1])

def get_house_for_degree(degree: float, houses: list[dict]) -> int:
    """Определяет, в какой дом попадает конкретный градус (0-360)"""
    deg = degree % 360
    for i in range(len(houses)):
        curr_h = houses[i]
        next_h = houses[(i + 1) % len(houses)]
        c1 = curr_h["abs_pos"]
        c2 = next_h["abs_pos"]
        if c1 > c2: 
            if deg >= c1 or deg < c2: return curr_h["house"]
        else:
            if c1 <= deg < c2: return curr_h["house"]
    return 1

def measure_time(func):
    """Декоратор для замера времени выполнения функции."""
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        # print(f"[{func.__name__}] took {end - start:.4f} seconds") # Раскомментировать для дебага
        return result
    return wrapper

def get_utc_jd_from_input(inp) -> float:
    """Универсальный расчет Юлианского дня (UTC) из BirthInput с учетом таймзоны."""
    try:
        date_str = inp.date.replace('/', '-')
        if '-' in date_str:
            parts = date_str.split('-')
            y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
        else:
            dt_obj = datetime.strptime(date_str, "%Y-%m-%d")
            y, m, d = dt_obj.year, dt_obj.month, dt_obj.day
    except:
         dt_obj = datetime.strptime(inp.date, "%Y-%m-%d")
         y, m, d = dt_obj.year, dt_obj.month, dt_obj.day

    try:
        t_parts = inp.time.split(':')
        h = int(t_parts[0])
        mn = int(t_parts[1])
        s = float(t_parts[2]) if len(t_parts) > 2 else 0.0
    except:
        h, mn, s = 12, 0, 0

    offset_hours = 0.0
    tz_str = inp.tz
    try:
        if tz_str:
            tz = pytz.timezone(tz_str)
            dt_local = datetime(y, m, d, h, mn, int(s))
            dt_aware = tz.localize(dt_local)
            offset_duration = dt_aware.utcoffset()
            offset_hours = offset_duration.total_seconds() / 3600.0
    except Exception as e:
        print(f"⚠️ Timezone Error ({tz_str}): {e}. Using UTC.")
        offset_hours = 0.0

    hour_decimal_local = h + (mn / 60.0) + (s / 3600.0)
    hour_decimal_utc = hour_decimal_local - offset_hours
    
    return swe.julday(y, m, d, hour_decimal_utc)