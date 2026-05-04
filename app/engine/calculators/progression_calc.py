import swisseph as swe
import datetime
from app.engine.core.models import BirthInput
from app.engine.calculators.solar_calc import get_utc_jd

def calculate_progressed_input(natal_inp: BirthInput, target_date: str) -> BirthInput:
    """
    Рассчитывает Вторичные Прогрессии (1 тропический год = 1 эфемеридный день)
    """
    # 1. Получаем натальный JD (в UTC)
    natal_jd_utc = get_utc_jd(natal_inp)
    
    # 2. Получаем целевой JD (на полдень целевой даты)
    y_t, m_t, d_t = map(int, target_date.split('-'))
    target_jd_utc = swe.julday(y_t, m_t, d_t, 12.0)
    
    # Тропический год в днях (максимальная точность)
    TROPICAL_YEAR = 365.242199
    
    # 3. Вычисляем точный возраст в годах на целевую дату
    age_in_years = (target_jd_utc - natal_jd_utc) / TROPICAL_YEAR
    
    # 4. Прибавляем возраст (в днях) к натальной дате (1 год = 1 день)
    progressed_jd_utc = natal_jd_utc + age_in_years
    
    # 5. Конвертируем обратно в дату и время
    y_p, m_p, d_p, h_decimal_utc = swe.revjul(progressed_jd_utc)
    
    # Аккуратно переводим десятичные часы в часы, минуты и секунды
    dt_base = datetime.datetime(y_p, m_p, d_p) + datetime.timedelta(hours=h_decimal_utc)
    
    # Возвращаем новые данные (прогрессии всегда строятся на место рождения!)
    return BirthInput(
        name=f"Progressed for {target_date}",
        date=dt_base.strftime("%Y-%m-%d"),
        time=dt_base.strftime("%H:%M:%S"),
        tz="0.0",  # Мы посчитали в UTC
        lat=natal_inp.lat,
        lon=natal_inp.lon,
        house_system=natal_inp.house_system,
        node_type=natal_inp.node_type
    )