import swisseph as swe
import datetime
from app.engine.core.models import BirthInput
from app.engine.core.utils import parse_ymd
# Импортируем вашу функцию из Соляра, чтобы не дублировать код
from app.engine.calculators.solar_calc import get_utc_jd

def find_nearest_lunar_return_jd(natal_jd_utc: float, target_jd_utc: float) -> float:
    """Ищет ближайший момент возвращения Луны в натальную точку от заданной даты"""
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED
    
    # 1. Позиция натальной Луны
    res_natal = swe.calc_ut(natal_jd_utc, swe.MOON, flags)
    moon_natal_lon = res_natal[0][0] 

    # 2. Итеративный поиск
    jd_iter = target_jd_utc

    for _ in range(20): # Обычно хватает 3-4 итераций
        res = swe.calc_ut(jd_iter, swe.MOON, flags)
        moon_curr_lon = res[0][0] # Текущая долгота
        moon_speed = res[0][3]    # Скорость Луны (около 13° в день)

        delta = moon_natal_lon - moon_curr_lon
        if delta < -180: delta += 360
        elif delta > 180: delta -= 360

        if abs(delta) < 0.00001:
            break
        
        # Сдвигаем время пропорционально скорости Луны
        jd_iter += delta / moon_speed
        
    return jd_iter

def calculate_lunar_return_input(natal_inp: BirthInput, target_date: str, loc_lat: float, loc_lon: float, loc_tz: str) -> BirthInput:
    """
    Рассчитывает точное время Лунара и возвращает готовый объект BirthInput.
    """
    natal_jd_utc = get_utc_jd(natal_inp) 
    
    # Конвертируем целевую дату в JD (начинаем поиск с полудня)
    y, m, d = parse_ymd(target_date)
    target_jd_utc = swe.julday(y, m, d, 12.0)
    
    lunar_jd_utc = find_nearest_lunar_return_jd(natal_jd_utc, target_jd_utc)
    
    # Конвертируем в дату/время UTC
    y_l, m_l, d_l, h_decimal_utc = swe.revjul(lunar_jd_utc)
    
    # Считаем локальное время для НОВОГО места
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
    
    dt_base = datetime.datetime(y_l, m_l, d_l) + datetime.timedelta(hours=h_decimal_local)
    lunar_date_str = dt_base.strftime("%Y-%m-%d")
    lunar_time_str = dt_base.strftime("%H:%M:%S")
    
    return BirthInput(
        name=f"Lunar {target_date}",
        date=lunar_date_str,
        time=lunar_time_str,
        tz=loc_tz,
        lat=loc_lat,
        lon=loc_lon
    )