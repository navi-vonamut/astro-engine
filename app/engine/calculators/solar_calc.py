import swisseph as swe
import datetime
from app.engine.core.models import BirthInput
from app.engine.core.utils import parse_ymd, parse_hm

def get_utc_jd(inp: BirthInput) -> float:
    """Превращает вводные данные в Julian Day (UTC)"""
    y, m, d = parse_ymd(inp.date)
    hh, mm = parse_hm(inp.time)
    
    offset_hours = 0.0
    try:
        val = str(inp.tz).replace("+", "")
        if ":" in val:
            parts = val.split(":")
            sign = -1 if "-" in str(inp.tz) else 1
            offset_hours = sign * (float(parts[0]) + float(parts[1])/60.0)
        else:
            offset_hours = float(val)
    except:
        offset_hours = 0.0

    # Конвертируем локальное время в UTC
    utc_hour = hh + (mm / 60.0) - offset_hours
    return swe.julday(y, m, d, utc_hour)

def find_exact_solar_return_jd(natal_jd_utc: float, year: int) -> float:
    """Ищет точный момент возвращения Солнца в натальную точку"""
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED
    
    # 1. Позиция натального Солнца
    res_natal = swe.calc_ut(natal_jd_utc, swe.SUN, flags)
    sun_natal_lon = res_natal[0][0] 

    # День рождения (месяц, день)
    y_n, m_n, d_n, _ = swe.revjul(natal_jd_utc)
    
    # Старт поиска: полдень дня рождения в целевом году
    jd_iter = swe.julday(year, m_n, d_n, 12.0)

    for _ in range(15):
        res = swe.calc_ut(jd_iter, swe.SUN, flags)
        vals = res[0]
        
        sun_curr_lon = vals[0] # Долгота
        sun_speed = vals[3]    # Скорость (долгота/день)

        delta = sun_natal_lon - sun_curr_lon
        if delta < -180: delta += 360
        elif delta > 180: delta -= 360

        if abs(delta) < 0.00001:
            break
        
        jd_iter += delta / sun_speed
        
    return jd_iter

def calculate_solar_return_input(natal_inp: BirthInput, year: int, loc_lat: float, loc_lon: float, loc_tz: str) -> BirthInput:
    """
    Рассчитывает точное время Соляра и возвращает готовый объект BirthInput 
    для построения новой карты на место встречи Соляра.
    """
    # 1. Находим момент по натальным данным (UTC)
    natal_jd_utc = get_utc_jd(natal_inp) 
    solar_jd_utc = find_exact_solar_return_jd(natal_jd_utc, year)
    
    # 2. Конвертируем в дату/время UTC
    y, m, d, h_decimal_utc = swe.revjul(solar_jd_utc)
    
    # 3. Считаем локальное время для НОВОГО места
    offset = 0.0
    try:
        val = str(loc_tz).replace("+", "")
        if ":" in val:
            parts = val.split(":")
            sign = -1 if "-" in str(loc_tz) else 1
            offset = sign * (float(parts[0]) + float(parts[1])/60.0)
        else:
            offset = float(val)
    except:
        pass
        
    h_decimal_local = h_decimal_utc + offset
    
    dt_base = datetime.datetime(y, m, d) + datetime.timedelta(hours=h_decimal_local)
    solar_date_str = dt_base.strftime("%Y-%m-%d")
    solar_time_str = dt_base.strftime("%H:%M:%S")
    
    # Возвращаем готовый инпут для движка
    return BirthInput(
        name=f"Solar {year}",
        date=solar_date_str,
        time=solar_time_str,
        tz=loc_tz,
        lat=loc_lat,
        lon=loc_lon
    )