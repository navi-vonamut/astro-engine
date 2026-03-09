from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import datetime

from kerykeion import AstrologicalSubjectFactory, AspectsFactory
from kerykeion.chart_data_factory import ChartDataFactory
import swisseph as swe
import re
import tempfile
import os
from kerykeion import KerykeionChartSVG

_OFFSET_RE = re.compile(r"^([+-])(\d{2}):?(\d{2})$")

def _norm_date(s: str) -> str:
    s = (s or "").strip().replace("/", "-")
    return s

def _tz_to_pytz(tz: str) -> str:
    tz = (tz or "").strip()
    if not tz: return "UTC"
    if "/" in tz and not tz.startswith(("+", "-")): return tz
    m = _OFFSET_RE.match(tz)
    if not m: return "UTC"
    sign, hh, mm = m.group(1), int(m.group(2)), int(m.group(3))
    if mm != 0: return "UTC"
    if sign == "+": return f"Etc/GMT-{hh}"
    return f"Etc/GMT+{hh}"

def _parse_ymd(date_str: str) -> tuple[int, int, int]:
    d = _norm_date(date_str)
    y, m, day = d.split("-")
    return int(y), int(m), int(day)

def _parse_hm(time_str: str) -> tuple[int, int]:
    t = (time_str or "").strip()
    parts = t.split(":")
    if len(parts) < 2: raise ValueError(f"Bad time format: {time_str}")
    return int(parts[0]), int(parts[1])

@dataclass(frozen=True)
class BirthInput:
    name: str
    date: str
    time: str
    tz: str
    lat: float
    lon: float
    house_system: str = "P"
    node_type: str = "true"

class KerykeionEngine:
    def build_subject(self, inp: BirthInput):
        y, m, d = _parse_ymd(inp.date)
        hh, mm = _parse_hm(inp.time)
        return AstrologicalSubjectFactory.from_birth_data(
            name=inp.name, year=y, month=m, day=d, hour=hh, minute=mm,
            lng=float(inp.lon), lat=float(inp.lat),
            tz_str=_tz_to_pytz(str(inp.tz)), houses_system_identifier=inp.house_system, online=False,
        )
    
    def _get_swisseph_speed(self, jd: float, p_name: str) -> float:
        mapping = {
            "Sun": 0, "Moon": 1, "Mercury": 2, "Venus": 3, "Mars": 4,
            "Jupiter": 5, "Saturn": 6, "Uranus": 7, "Neptune": 8, "Pluto": 9,
            "Mean_Lilith": 11, "True_North_Lunar_Node": 11, "Chiron": 15,
        }
        pid = mapping.get(p_name)
        if pid is None: return 0.0
        try:
            # calc_ut returns ((lon, lat, dist, speed...), rflag)
            res = swe.calc_ut(jd, pid, 2 | 256) 
            return res[0][3]
        except: return 0.0

    def _extract_planet(self, subject, attr_name: str, display_name: str) -> Optional[Dict[str, Any]]:
        attr_lower = attr_name.lower()
        point = getattr(subject, attr_lower, None)
        
        # Умный поиск по алиасам для Kerykeion
        if not point:
            if display_name == "Mean_Lilith":
                point = getattr(subject, "mean_apogee", None) or getattr(subject, "lilith", None)
            elif display_name == "True_North_Lunar_Node":
                point = getattr(subject, "true_north_lunar_node", None) or getattr(subject, "true_node", None) or getattr(subject, "north_node", None)
            elif display_name == "Mean_North_Lunar_Node":
                point = getattr(subject, "mean_node", None)
                
        # Если Kerykeion справился:
        if point:
            real_speed = self._get_swisseph_speed(subject.julian_day, display_name)
            house_val = getattr(point, "house", None)
            if isinstance(house_val, str):
                house_map = {"First_House": 1, "Second_House": 2, "Third_House": 3, "Fourth_House": 4, 
                             "Fifth_House": 5, "Sixth_House": 6, "Seventh_House": 7, "Eighth_House": 8, 
                             "Ninth_House": 9, "Tenth_House": 10, "Eleventh_House": 11, "Twelfth_House": 12}
                house_val = house_map.get(house_val, 1)

            return {
                "name": display_name,
                "sign": getattr(point, "sign", ""),
                "sign_id": getattr(point, "sign_num", 0),
                "degree": getattr(point, "position", 0.0),
                "abs_pos": getattr(point, "abs_pos", 0.0),
                "house": house_val,
                "is_retro": getattr(point, "retrograde", real_speed < 0),
                "speed": real_speed,
                "is_stationary": abs(real_speed) < 0.05
            }
            
        # === 100% ЖЕЛЕЗОБЕТОННЫЙ ФОЛЛБЕК НА SWISSEPH ===
        # Если точка так и не найдена, рассчитываем ее напрямую!
        swe_mapping = {
            "Mean_North_Lunar_Node": swe.MEAN_NODE,
            "True_North_Lunar_Node": swe.TRUE_NODE,
            "Mean_Lilith": swe.MEAN_APOG,
            "Chiron": swe.CHIRON
        }
        
        if display_name in swe_mapping:
            pid = swe_mapping[display_name]
            # Запрашиваем точные координаты у эфемерид
            res = swe.calc_ut(subject.julian_day, pid, swe.FLG_SWIEPH | swe.FLG_SPEED)
            lon = res[0][0]
            speed = res[0][3]
            
            signs_short = ["Ari", "Tau", "Gem", "Can", "Leo", "Vir", "Lib", "Sco", "Sag", "Cap", "Aqu", "Pis"]
            sign_id = int(lon // 30)
            
            return {
                "name": display_name,
                "sign": signs_short[sign_id],
                "sign_id": sign_id,
                "degree": lon % 30,
                "abs_pos": lon,
                "house": None, # Дом присвоим чуть позже, когда посчитаем куспиды
                "is_retro": speed < 0,
                "speed": speed,
                "is_stationary": abs(speed) < 0.05
            }
            
        return None
    
    def _get_house_for_degree(self, degree: float, houses: List[Dict]) -> int:
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

    def _is_combust(self, planet_abs_pos: float, sun_abs_pos: float) -> bool:
        diff = abs(planet_abs_pos - sun_abs_pos)
        if diff > 180: diff = 360 - diff
        return diff < 8.5

    # === ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ДЛЯ СОЛЯРА ===
    def _get_utc_jd(self, inp: BirthInput) -> float:
        """Помощник: превращает ввод в Julian Day (UTC)"""
        y, m, d = _parse_ymd(inp.date)
        hh, mm = _parse_hm(inp.time)
        
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

    def _find_exact_solar_return_jd(self, natal_jd_utc: float, year: int) -> float:
        """Математика Соляра: ищет точный момент возвращения Солнца"""
        flags = swe.FLG_SWIEPH | swe.FLG_SPEED
        
        # 1. Позиция натального Солнца
        res_natal = swe.calc_ut(natal_jd_utc, swe.SUN, flags)
        # res_natal = ((lon, lat, dist, speed...), rflag)
        sun_natal_lon = res_natal[0][0] # <-- ИСПРАВЛЕНО: берем [0] (кортеж данных) и [0] (долгота)

        # День рождения (месяц, день)
        y_n, m_n, d_n, _ = swe.revjul(natal_jd_utc)
        
        # Старт поиска: полдень дня рождения в целевом году
        jd_iter = swe.julday(year, m_n, d_n, 12.0)

        for _ in range(15):
            res = swe.calc_ut(jd_iter, swe.SUN, flags)
            # res[0] - кортеж данных
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

    # === ГЛАВНЫЙ МЕТОД СОЛЯРА ===
    def solar_return(self, natal_inp: BirthInput, year: int, loc_lat: float, loc_lon: float, loc_tz: str) -> Dict[str, Any]:
        """
        Строит карту Соляра с учетом релокации.
        """
        print(f"\n[ENGINE] Соляр для {natal_inp.name}. Год: {year}. Локация: {loc_lat}, {loc_lon}")
        
        # 1. Находим момент по натальным данным (UTC)
        natal_jd_utc = self._get_utc_jd(natal_inp) 
        solar_jd_utc = self._find_exact_solar_return_jd(natal_jd_utc, year)
        
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
        
        import datetime
        dt_base = datetime.datetime(y, m, d) + datetime.timedelta(hours=h_decimal_local)
        solar_date_str = dt_base.strftime("%Y-%m-%d")
        solar_time_str = dt_base.strftime("%H:%M:%S")
        
        print(f"[ENGINE] Дата Соляра (Local): {solar_date_str} {solar_time_str}")

        # 4. Строим карту на НОВЫЕ координаты
        solar_input = BirthInput(
            name=f"Solar {year}",
            date=solar_date_str,
            time=solar_time_str,
            tz=loc_tz,
            lat=loc_lat,
            lon=loc_lon
        )
        
        chart = self.natal(solar_input)
        
        chart["meta"]["type"] = "solar_return"
        chart["meta"]["solar_year"] = year
        chart["meta"]["location_name"] = f"{loc_lat}, {loc_lon}" 
        
        return chart

    def natal(self, inp: BirthInput) -> Dict[str, Any]:
        subject = self.build_subject(inp)
        chart_data = ChartDataFactory.create_natal_chart_data(subject)
        chart_dump = chart_data.model_dump(mode="json")

        node_key = "True_North_Lunar_Node" if inp.node_type == "true" else "Mean_North_Lunar_Node"

        target_points = [
            ("Sun", "Sun"), ("Moon", "Moon"), ("Mercury", "Mercury"), 
            ("Venus", "Venus"), ("Mars", "Mars"), ("Jupiter", "Jupiter"), 
            ("Saturn", "Saturn"), ("Uranus", "Uranus"), ("Neptune", "Neptune"), 
            ("Pluto", "Pluto"), ("Chiron", "Chiron"),
            (node_key, node_key), ("Mean_Lilith", "Mean_Lilith")
        ]
        
        planets_list = []
        
    # 1. Собираем основные планеты и точки
        for attr, label in target_points:
            p = self._extract_planet(subject, attr, label)
            if p: planets_list.append(p)

    # 2. СНАЧАЛА ФОРМИРУЕМ ДОМА (Они нужны для узлов и фиктивных точек!)
        houses_list = []
        house_names = [
            "first_house", "second_house", "third_house", "fourth_house", 
            "fifth_house", "sixth_house", "seventh_house", "eighth_house", 
            "ninth_house", "tenth_house", "eleventh_house", "twelfth_house"
        ]
        for i, h_attr in enumerate(house_names):
            h_obj = getattr(subject, h_attr, None)
            if h_obj:
                houses_list.append({
                    "house": i + 1,
                    "sign": getattr(h_obj, "sign", ""),
                    "degree": getattr(h_obj, "position", 0.0),
                    "abs_pos": getattr(h_obj, "abs_pos", 0.0)
                })

        # === ПАТЧ: Расселяем по домам те точки, которые мы посчитали вручную ===
        for p in planets_list:
            if p.get("house") is None:
                p["house"] = self._get_house_for_degree(p["abs_pos"], houses_list)

        # Общий массив знаков для точек
        signs_full = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
        signs_short = ["Ari", "Tau", "Gem", "Can", "Leo", "Vir", "Lib", "Sco", "Sag", "Cap", "Aqu", "Pis"]

        # 3. Высчитываем Южный Узел (отталкиваясь от найденного Северного)
        north_node = next((p for p in planets_list if p["name"] in ["True_North_Lunar_Node", "Mean_North_Lunar_Node"]), None)
        
        if north_node:
            sn_abs_pos = (north_node["abs_pos"] + 180) % 360
            sn_sign_id = int(sn_abs_pos // 30)
            sn_label = "True_South_Lunar_Node" if inp.node_type == "true" else "Mean_South_Lunar_Node"
            
            planets_list.append({
                "name": sn_label,
                "sign": signs_short[sn_sign_id],
                "sign_id": sn_sign_id,
                "degree": sn_abs_pos % 30,
                "abs_pos": sn_abs_pos,
                # Если у вас уже рассчитаны Дома на этом этапе, используем их, иначе None (и он подхватится патчем ниже)
                "house": self._get_house_for_degree(sn_abs_pos, houses_list) if houses_list else None,
                "is_retro": north_node.get("is_retro", False),
                "speed": north_node.get("speed", 0.0),
                "is_stationary": north_node.get("is_stationary", False)
            })

        # 4. РАССЧИТЫВАЕМ ФИКТИВНЫЕ ТОЧКИ ВРУЧНУЮ
        try:
            # Вертекс
            cusps, ascmc = swe.houses(subject.julian_day, inp.lat, inp.lon, str(inp.house_system).encode('ascii'))
            vertex_abs = ascmc[3]
            planets_list.append({
                "name": "Vertex",
                "sign": signs_short[int(vertex_abs // 30)],
                "sign_id": int(vertex_abs // 30),
                "degree": vertex_abs % 30,
                "abs_pos": vertex_abs,
                "house": self._get_house_for_degree(vertex_abs, houses_list), # <-- ТЕПЕРЬ ИЩЕМ В ПРАВИЛЬНОМ МАССИВЕ
                "is_retro": False,
                "speed": 0.0,
                "is_stationary": False
            })

            # Фортуна
            asc_obj = getattr(subject, "first_house", None)
            sun_obj = getattr(subject, "sun", None)
            moon_obj = getattr(subject, "moon", None)
            
            if asc_obj and sun_obj and moon_obj:
                day_houses = ["Seventh_House", "Eighth_House", "Ninth_House", "Tenth_House", "Eleventh_House", "Twelfth_House"]
                is_day_chart = getattr(sun_obj, "house", "") in day_houses
                
                if is_day_chart:
                    pf_abs = (asc_obj.abs_pos + moon_obj.abs_pos - sun_obj.abs_pos) % 360
                else:
                    pf_abs = (asc_obj.abs_pos + sun_obj.abs_pos - moon_obj.abs_pos) % 360
                    
                planets_list.append({
                    "name": "Fortune",
                    "sign": signs_short[int(pf_abs // 30)],
                    "sign_id": int(pf_abs // 30),
                    "degree": pf_abs % 30,
                    "abs_pos": pf_abs,
                    "house": self._get_house_for_degree(pf_abs, houses_list), # <-- ТЕПЕРЬ ИЩЕМ В ПРАВИЛЬНОМ МАССИВЕ
                    "is_retro": False,
                    "speed": 0.0,
                    "is_stationary": False
                })
        except Exception as e:
            print(f"[ENGINE ERROR] Ошибка расчета фиктивных точек: {e}")

        # 5. Добавляем Углы карты (ASC, DSC, MC, IC)
        angles = [
            ("Ascendant", getattr(subject, "first_house", None)),
            ("Descendant", getattr(subject, "seventh_house", None)),
            ("Medium_Coeli", getattr(subject, "tenth_house", None)),
            ("Imum_Coeli", getattr(subject, "fourth_house", None))
        ]
        for ang_name, ang_obj in angles:
            if ang_obj:
                planets_list.append({
                    "name": ang_name,
                    "sign": getattr(ang_obj, "sign", ""),
                    "sign_id": getattr(ang_obj, "sign_num", 0),
                    "degree": getattr(ang_obj, "position", 0.0),
                    "abs_pos": getattr(ang_obj, "abs_pos", 0.0),
                    "house": None, 
                    "is_retro": False, 
                    "speed": 0.0,
                    "is_stationary": False
                })

        houses_list = []
        house_names = [
            "first_house", "second_house", "third_house", "fourth_house", 
            "fifth_house", "sixth_house", "seventh_house", "eighth_house", 
            "ninth_house", "tenth_house", "eleventh_house", "twelfth_house"
        ]
        for i, h_attr in enumerate(house_names):
            h_obj = getattr(subject, h_attr, None)
            if h_obj:
                houses_list.append({
                    "house": i + 1,
                    "sign": getattr(h_obj, "sign", ""),
                    "degree": getattr(h_obj, "position", 0.0),
                    "abs_pos": getattr(h_obj, "abs_pos", 0.0)
                })

        # --- 6. ПОЛНОСТЬЮ КАСТОМНЫЙ РАСЧЕТ ВСЕХ АСПЕКТОВ (В СТИЛЕ ASTRO-SEEK) ---
        clean_aspects = []
        
        # Правила: Угол -> (Название, Орбис_для_Планет, Орбис_для_Фиктивных)
        aspect_rules = {
            # Мажорные
            0:   ("conjunction", 8.0, 2.5),
            60:  ("sextile", 6.0, 2.0),
            90:  ("square", 8.0, 2.5),
            120: ("trine", 8.0, 2.5),
            180: ("opposition", 8.0, 2.5),
            # Минорные и творческие
            30:  ("semisextile", 1.5, 1.0),
            45:  ("semisquare", 1.5, 1.0),
            72:  ("quintile", 1.5, 1.0),
            135: ("sesquiquadrate", 1.5, 1.0),
            144: ("biquintile", 1.5, 1.0),
            150: ("quincunx", 2.0, 1.5)
        }

        # Фиктивные точки и углы (к ним орбис всегда строгий, иначе карта превратится в кашу)
        strict_points = ["True_North_Lunar_Node", "True_South_Lunar_Node", "Mean_Lilith", "Fortune", "Vertex", "Ascendant", "Descendant", "Medium_Coeli", "Imum_Coeli"]

        # Словарь для запроса Склонений (Declination) из швейцарских эфемерид
        swisseph_ids = {
            "Sun": swe.SUN, "Moon": swe.MOON, "Mercury": swe.MERCURY, "Venus": swe.VENUS,
            "Mars": swe.MARS, "Jupiter": swe.JUPITER, "Saturn": swe.SATURN, "Uranus": swe.URANUS,
            "Neptune": swe.NEPTUNE, "Pluto": swe.PLUTO, "Chiron": swe.CHIRON,
            "True_North_Lunar_Node": swe.TRUE_NODE, "Mean_Lilith": swe.MEAN_APOG
        }

        def get_declination(p_name, jd):
            if p_name in swisseph_ids:
                try:
                    # FLG_EQUATORIAL отдаст нам экваториальные координаты (включая Склонение)
                    res, _ = swe.calc_ut(jd, swisseph_ids[p_name], swe.FLG_EQUATORIAL)
                    return res[1]  # Индекс 1 — это склонение
                except Exception:
                    return None
            return None

        # Перебираем каждую уникальную пару планет/точек
        for i in range(len(planets_list)):
            for j in range(i + 1, len(planets_list)):
                p1 = planets_list[i]
                p2 = planets_list[j]
                
                # Игнорируем очевидные оппозиции (Узлы между собой, ASC-DSC, MC-IC)
                if p1["name"] == "True_North_Lunar_Node" and p2["name"] == "True_South_Lunar_Node": continue
                if p1["name"] == "Ascendant" and p2["name"] == "Descendant": continue
                if p1["name"] == "Medium_Coeli" and p2["name"] == "Imum_Coeli": continue
                
                is_strict = (p1["name"] in strict_points) and (p2["name"] in strict_points)
                
                # === РАСЧЕТ АСПЕКТОВ ПО ДОЛГОТЕ (Обычные) ===
                diff = abs(p1["abs_pos"] - p2["abs_pos"])
                if diff > 180:
                    diff = 360 - diff
                    
                for angle, (asp_name, orb_normal, orb_strict) in aspect_rules.items():
                    max_orb = orb_strict if is_strict else orb_normal
                    orb = abs(diff - angle)
                    if orb <= max_orb:
                        clean_aspects.append({
                            "p1": p1["name"],
                            "p2": p2["name"],
                            "type": asp_name,
                            "orb": round(orb, 4),
                            # Сходимость (Applying) можно высчитать по скорости, но пока ставим False 
                            # (если скорости направлены друг к другу)
                            "is_applying": False 
                        })
                
                # === РАСЧЕТ АСПЕКТОВ ПО СКЛОНЕНИЮ (Параллели) ===
                # Параллели обычно смотрят только для реальных планет (не для углов/фиктивных точек)
                if not is_strict:
                    decl1 = get_declination(p1["name"], subject.julian_day)
                    decl2 = get_declination(p2["name"], subject.julian_day)
                    
                    if decl1 is not None and decl2 is not None:
                        # Расстояние по модулю склонения
                        diff_decl = abs(abs(decl1) - abs(decl2))
                        
                        # Орбис для параллелей очень жесткий: максимум 1.2 градуса
                        if diff_decl <= 1.2: 
                            is_same_sign = (decl1 * decl2) > 0 # Если знаки одинаковые (оба +, или оба -)
                            asp_type = "parallel" if is_same_sign else "contraparallel"
                            clean_aspects.append({
                                "p1": p1["name"],
                                "p2": p2["name"],
                                "type": asp_type,
                                "orb": round(diff_decl, 4),
                                "is_applying": False
                            })
        return {
            "meta": {
                "engine": "kerykeion_v5",
                "subject": inp.name,
                "datetime": f"{_norm_date(inp.date)}T{inp.time}",
                "location": {"lat": inp.lat, "lon": inp.lon}
            },
            "planets": planets_list,
            "houses": houses_list,
            "aspects": clean_aspects,
            "balance": {
                "elements": chart_dump.get("element_distribution"),
                "qualities": chart_dump.get("quality_distribution")
            }
        }
    
    def synastry_aspects(self, p1: BirthInput, p2: BirthInput) -> List[Dict[str, Any]]:
        s1 = self.build_subject(p1)
        s2 = self.build_subject(p2)
        
        try:
            res = AspectsFactory.dual_chart_aspects(s1, s2)
        except Exception as e:
            print(f"[ENGINE ERROR] AspectsFactory error: {e}")
            return []

        PLANET_WHITELIST = {
            "Sun", "Moon", "Mercury", "Venus", "Mars", 
            "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto",
            "Chiron", "True Node", "Lilith"
        }
        
        ALLOWED_ASPECTS = {"conjunction", "opposition", "square", "trine", "sextile"}
        
        aspects = []
        for a in res.aspects:
            d = a.model_dump(mode="json")
            
            p1_n = d.get("p1_name", "")
            p2_n = d.get("p2_name", "")
            raw_asp = d.get("aspect_name") or d.get("aspect") or ""
            asp_lower = raw_asp.lower()
            # Берем orbit, если его нет - ищем orb, если ничего нет - 0.0
            orb_raw = d.get("orbit", d.get("orb", 0.0)) 
            orb = float(orb_raw if orb_raw is not None else 0.0)

            if p1_n not in PLANET_WHITELIST or p2_n not in PLANET_WHITELIST:
                continue

            if asp_lower not in ALLOWED_ASPECTS:
                continue

            limit = 3.0
            if "Moon" in p1_n: limit = 8.0  
            elif "Sun" in p1_n: limit = 6.0
            elif p1_n in ["Mercury", "Venus", "Mars"]: limit = 5.0
            elif p1_n in ["Jupiter", "Saturn"]: limit = 4.0
            if any(x in p1_n for x in ["Node", "Lilith", "Chiron"]): limit = 1.5

            if abs(orb) > limit:
                continue

            aspects.append({
                "person1_object": p1_n,
                "aspect": raw_asp.title(),
                "person2_object": p2_n,
                "orb": orb,
            })
            
        return aspects

    def transits(self, natal_inp: BirthInput, transit_date: str) -> Dict[str, Any]:
        """ПРОДВИНУТЫЕ ТРАНЗИТЫ"""
        print(f"\n[ENGINE START] Transits for {natal_inp.name} on target date {transit_date}")
        
        natal_data = self.natal(natal_inp)
        natal_houses = natal_data["houses"]
        
        y, m, d = _parse_ymd(transit_date)
        transit_inp = BirthInput(
            name="Transit", date=f"{y:04d}-{m:02d}-{d:02d}", time="12:00:00",
            tz=natal_inp.tz, lat=natal_inp.lat, lon=natal_inp.lon 
        )
        
        transit_chart = self.natal(transit_inp)
        transit_planets_enriched = []
        for p in transit_chart["planets"]:
            in_house = self._get_house_for_degree(p["abs_pos"], natal_houses)
            p_enriched = p.copy()
            p_enriched["in_natal_house"] = in_house
            transit_planets_enriched.append(p_enriched)

        aspects = self.synastry_aspects(transit_inp, natal_inp)
        
        transit_aspects = []
        for a in aspects:
            transit_aspects.append({
                "transit_planet": a["person1_object"],
                "aspect": a["aspect"],
                "natal_planet": a["person2_object"],
                "orb": a["orb"],
            })

        print(f"[ENGINE RESULT] Final Aspect Count: {len(transit_aspects)}")
        return {
            "meta": {"type": "transits", "date": transit_date, "target": natal_inp.name},
            "transit_planets": transit_planets_enriched,
            "aspects": transit_aspects
        }

    def horary(self, inp: BirthInput, question: str) -> Dict[str, Any]:
        chart = self.natal(inp)
        sun_pos = next((p["abs_pos"] for p in chart["planets"] if p["name"] == "Sun"), 0.0)
        enriched_planets = []
        for p in chart["planets"]:
            is_combust = False
            if p["name"] != "Sun" and p["name"] not in ["True Node", "Lilith", "Mean Node"]:
                 is_combust = self._is_combust(p["abs_pos"], sun_pos)
            p["is_combust"] = is_combust
            enriched_planets.append(p)
        chart["planets"] = enriched_planets
        chart["meta"]["type"] = "horary"
        chart["meta"]["question"] = question
        return chart

    def synastry(self, p1: BirthInput, p2: BirthInput) -> Dict[str, Any]:
        c1 = self.natal(p1)
        c2 = self.natal(p2)
        aspects = self.synastry_aspects(p1, p2)
        
        p1_in_p2_houses = []
        for p in c1["planets"]:
            house_in_p2 = self._get_house_for_degree(p["abs_pos"], c2["houses"])
            p1_in_p2_houses.append({
                "planet": p["name"],
                "in_partner_house": house_in_p2,
                "partner_house_sign": c2["houses"][house_in_p2-1]["sign"]
            })

        p2_in_p1_houses = []
        for p in c2["planets"]:
            house_in_p1 = self._get_house_for_degree(p["abs_pos"], c1["houses"])
            p2_in_p1_houses.append({
                "planet": p["name"],
                "in_partner_house": house_in_p1,
                "partner_house_sign": c1["houses"][house_in_p1-1]["sign"]
            })

        return {
            "meta": {"type": "synastry", "p1": p1.name, "p2": p2.name},
            "aspects": aspects,
            "overlays": {
                "owner_planets_in_partner_houses": p1_in_p2_houses,
                "partner_planets_in_owner_houses": p2_in_p1_houses
            }
        }
    
    def get_natal_svg(self, inp: BirthInput) -> str:
        subject = self.build_subject(inp)
        with tempfile.TemporaryDirectory() as tmpdir:
            chart = KerykeionChartSVG(subject, chart_type="Natal", new_output_directory=tmpdir)
            chart.makeSVG()
            
            # Находим и читаем сгенерированный файл
            svg_file = [f for f in os.listdir(tmpdir) if f.endswith(".svg")][0]
            with open(os.path.join(tmpdir, svg_file), "r", encoding="utf-8") as f:
                return f.read()