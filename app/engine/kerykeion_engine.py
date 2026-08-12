from __future__ import annotations
from typing import Any, Dict, List, Optional
import math

from kerykeion import AstrologicalSubjectFactory
from kerykeion.chart_data_factory import ChartDataFactory
import swisseph as swe

from app.engine.core.models import BirthInput
from app.engine.core.utils import norm_date, tz_to_pytz, parse_ymd, parse_hm
from app.engine.render.svg_builder import build_natal_svg
from app.engine.core.utils import get_house_for_degree

from app.engine.core.constants import (
    SWISSEPH_OBJECTS, KERYKEION_HOUSES, SIGNS_SHORT, TARGET_POINTS_BASE, SIGN_RULERS_BY_ID
)

from app.engine.calculators.synastry_calc import get_synastry_aspects, calculate_house_overlays
from app.engine.calculators.composite_calc import get_composite_planets, get_composite_houses
from app.engine.calculators.solar_calc import calculate_solar_return_input
from app.engine.calculators.lunar_calc import calculate_lunar_return_input
from app.engine.calculators.progression_calc import calculate_progressed_input
from app.engine.calculators.directions_calc import (
    calculate_direction_arc, calculate_directed_chart, calculate_directional_aspects
)
from app.engine.calculators.rectification_calc import calculate_rectification
from app.engine.calculators.electional_calc import generate_daily_inputs, analyze_electional_day
from app.engine.calculators.aspects_calc import calculate_natal_aspects
from app.engine.analyzers.scoring import get_compensatory_data
from app.engine.analyzers.jones_patterns import calculate_jones_pattern
from app.engine.analyzers.dominants import calculate_dominants
from app.engine.analyzers.aspect_patterns import calculate_aspect_patterns
from app.engine.analyzers.planet_status import calculate_planet_status
from app.engine.calculators.content_calc import generate_content_events, generate_lunar_calendar
from app.engine.analyzers.synastry_scoring import calculate_synastry_indices

class KerykeionEngine:
    def __init__(self):
        # 🔥 Жестко указываем путь к системной папке с эфемеридами,
        # чтобы переопределить дефолтные настройки Kerykeion
        swe.set_ephe_path('/usr/share/swisseph')
    def build_subject(self, inp: BirthInput):
        y, m, d = parse_ymd(inp.date)
        hh, mm = parse_hm(inp.time)
        return AstrologicalSubjectFactory.from_birth_data(
            name=inp.name, year=y, month=m, day=d, hour=hh, minute=mm,
            lng=float(inp.lon), lat=float(inp.lat),
            tz_str=tz_to_pytz(str(inp.tz)), houses_system_identifier=inp.house_system, online=False,
        )
    
    def _get_swisseph_speed(self, jd: float, p_name: str) -> float:
        pid = SWISSEPH_OBJECTS.get(p_name)
        if pid is None: return 0.0
        try:
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
        if display_name in SWISSEPH_OBJECTS:
            pid = SWISSEPH_OBJECTS[display_name]
            res = swe.calc_ut(subject.julian_day, pid, swe.FLG_SWIEPH | swe.FLG_SPEED)
            lon = res[0][0]
            speed = res[0][3]
            
            sign_id = int(lon // 30)
            
            return {
                "name": display_name,
                "sign": SIGNS_SHORT[sign_id], 
                "sign_id": sign_id,
                "degree": lon % 30,
                "abs_pos": lon,
                "house": None, 
                "is_retro": speed < 0,
                "speed": speed,
                "is_stationary": abs(speed) < 0.05
            }
            
        return None

    def _is_combust(self, planet_abs_pos: float, sun_abs_pos: float) -> bool:
        diff = abs(planet_abs_pos - sun_abs_pos)
        if diff > 180: diff = 360 - diff
        return diff < 8.5

    def _get_aspect_state(self, t_pos: float, t_speed: float, n_pos: float, aspect_angle: float) -> str:
        def get_orb(p1, p2):
            diff = abs(p1 - p2)
            if diff > 180: diff = 360 - diff
            return abs(diff - aspect_angle)

        current_orb = get_orb(t_pos, n_pos)
        
        # Сдвигаем транзитную планету вперед на 0.1 дня (учитывая ее реальную скорость)
        next_pos = (t_pos + (t_speed * 0.1)) % 360
        next_orb = get_orb(next_pos, n_pos)

        if current_orb < 0.1: 
            return "exact" # Экзакт (Точный)
        if next_orb < current_orb: 
            return "retrograde_applying" if t_speed < 0 else "applying" # Сходится
        return "retrograde_separating" if t_speed < 0 else "separating" # Расходится

    # === ГЛАВНЫЙ МЕТОД СОЛЯРА ===
    def solar_return(self, natal_inp: BirthInput, year: int, loc_lat: float, loc_lon: float, loc_tz: str, precession_corrected: bool = False) -> Dict[str, Any]:
        print(f"\n[ENGINE] Соляр для {natal_inp.name}. Год: {year}. Локация: {loc_lat}, {loc_lon}. Прецессия: {precession_corrected}")
        
        # 1. Получаем точную дату и время соляра
        solar_input = calculate_solar_return_input(natal_inp, year, loc_lat, loc_lon, loc_tz, precession_corrected)
        print(f"[ENGINE] Дата Соляра (Local): {solar_input.date} {solar_input.time}")
        
        # 2. Строим карту Соляра
        solar_chart = self.natal(solar_input)
        
        # 3. Строим Натальную карту (чтобы получить сетку домов и координаты планет)
        natal_chart = self.natal(natal_inp, lite=True)
        
        # 4. 🔥 МАГИЯ: Считаем наложения (Соляр на Натал)
        # Нам нужно знать, куда попали солярные точки (особенно ASC и MC) в натале
        solar_in_natal_houses = calculate_house_overlays(solar_chart["planets"], natal_chart["houses"])
        
        # И какие аспекты солярные планеты делают к натальным
        solar_to_natal_aspects = get_synastry_aspects(solar_chart["planets"], natal_chart["planets"])

        # Обогащаем мета-данные
        solar_chart["meta"]["type"] = "solar_return"
        solar_chart["meta"]["solar_year"] = year
        solar_chart["meta"]["location_name"] = f"{loc_lat}, {loc_lon}" 
        solar_chart["meta"]["birth_date"] = str(natal_inp.date)
        solar_chart["meta"]["name"] = natal_inp.name
        
        # Достаем самое важное для ИИ - где находится Солярный Асцендент в Натале
        solar_asc_overlay = next((o for o in solar_in_natal_houses if o["planet"] == "Ascendant"), None)
        if solar_asc_overlay:
            solar_chart["meta"]["solar_asc_in_natal_house"] = solar_asc_overlay["in_partner_house"]
            solar_chart["meta"]["solar_asc_in_natal_sign"] = solar_asc_overlay["partner_house_sign"]

        # 5. Добавляем блок наложений и натальную карту в ответ
        solar_chart["natal_chart"] = natal_chart
        solar_chart["overlays"] = {
            "solar_planets_in_natal_houses": solar_in_natal_houses,
            "solar_to_natal_aspects": solar_to_natal_aspects
        }
        
        solar_chart["meta"]["is_precession_corrected"] = precession_corrected
        
        return solar_chart
    
    # === ГЛАВНЫЙ МЕТОД ЛУНАРА ===
    def lunar_return(self, natal_inp: BirthInput, target_date: str, loc_lat: float, loc_lon: float, loc_tz: str) -> Dict[str, Any]:
        print(f"\n[ENGINE] Лунар для {natal_inp.name}. Отправная дата: {target_date}. Локация: {loc_lat}, {loc_lon}")
        
        # 1. Получаем точную дату и время лунара
        lunar_input = calculate_lunar_return_input(natal_inp, target_date, loc_lat, loc_lon, loc_tz)
        print(f"[ENGINE] Дата Лунара (Local): {lunar_input.date} {lunar_input.time}")
        
        # 2. Строим карту Лунара
        lunar_chart = self.natal(lunar_input)
        
        # 3. Строим Натальную карту
        natal_chart = self.natal(natal_inp, lite=True)
        
        # 4. Наложения Лунара на Натал (Используем наши мощные синастрические функции)
        lunar_in_natal_houses = calculate_house_overlays(lunar_chart["planets"], natal_chart["houses"])
        lunar_to_natal_aspects = get_synastry_aspects(lunar_chart["planets"], natal_chart["planets"])

        # Обогащаем мета-данные
        lunar_chart["meta"]["type"] = "lunar_return"
        lunar_chart["meta"]["target_date"] = target_date
        lunar_chart["meta"]["location_name"] = f"{loc_lat}, {loc_lon}" 
        
        # Важнейший маркер для ИИ - в какой дом натала попал Асцендент Лунара
        lunar_asc_overlay = next((o for o in lunar_in_natal_houses if o["planet"] == "Ascendant"), None)
        if lunar_asc_overlay:
            lunar_chart["meta"]["lunar_asc_in_natal_house"] = lunar_asc_overlay["in_partner_house"]

        # 5. Добавляем блок наложений в ответ
        lunar_chart["overlays"] = {
            "lunar_planets_in_natal_houses": lunar_in_natal_houses,
            "lunar_to_natal_aspects": lunar_to_natal_aspects
        }
        
        return lunar_chart

    # === ГЛАВНЫЙ МЕТОД ПРОГРЕССИЙ ===
    def secondary_progressions(self, natal_inp: BirthInput, target_date: str) -> Dict[str, Any]:
        print(f"\n[ENGINE] Прогрессии для {natal_inp.name} на {target_date}")
        
        # 1. Получаем прогрессивные данные (Сдвинутое время)
        prog_input = calculate_progressed_input(natal_inp, target_date)
        print(f"[ENGINE] Прогрессивная дата (UTC): {prog_input.date} {prog_input.time}")
        
        # 2. Строим Прогрессивную карту
        prog_chart = self.natal(prog_input)
        
        # 3. Строим Натальную карту
        natal_chart = self.natal(natal_inp, lite=True)
        
        # 4. Наложения Прогрессий на Натал
        prog_in_natal_houses = calculate_house_overlays(prog_chart["planets"], natal_chart["houses"])
        prog_to_natal_aspects = get_synastry_aspects(prog_chart["planets"], natal_chart["planets"])

        # Обогащаем мета-данные
        prog_chart["meta"]["type"] = "secondary_progressions"
        prog_chart["meta"]["target_date"] = target_date

        # Добавляем блок наложений
        prog_chart["overlays"] = {
            "progressed_planets_in_natal_houses": prog_in_natal_houses,
            "progressed_to_natal_aspects": prog_to_natal_aspects
        }
        
        return prog_chart
    
    # === ГЛАВНЫЙ МЕТОД ЭЛЕКТИВА (АСТРО-ПЛАНИРОВЩИК) ===
    def electional_search(self, start_date: str, end_date: str, lat: float, lon: float, tz: str, category: str = "business") -> Dict[str, Any]:
        print(f"\n[ENGINE] Элективный поиск с {start_date} по {end_date} для локации {lat}, {lon} (Категория: {category})")
        
        daily_inputs = generate_daily_inputs(start_date, end_date, lat, lon, tz)
        
        days_analysis = []
        for inp in daily_inputs:
            # Строим карту на каждый день
            day_chart = self.natal(inp)
            # Извлекаем скоринг и суть с учетом категории
            day_summary = analyze_electional_day(day_chart, category=category)
            days_analysis.append(day_summary)
            
        return {
            "meta": {
                "type": "electional_search",
                "category": category,
                "start_date": start_date,
                "end_date": end_date,
                "location": {"lat": lat, "lon": lon}
            },
            "days": days_analysis
        }

    # === ГЛАВНЫЙ МЕТОД НАТАЛА (С ПОДДЕРЖКОЙ LITE-РЕЖИМА) ===
    def natal(self, inp: BirthInput, lite: bool = False) -> Dict[str, Any]:
        subject = self.build_subject(inp)
        chart_data = ChartDataFactory.create_natal_chart_data(subject)
        chart_dump = chart_data.model_dump(mode="json")

        node_key = "True_North_Lunar_Node" if inp.node_type == "true" else "Mean_North_Lunar_Node"
        target_points = TARGET_POINTS_BASE + [(node_key, node_key)]
        
        planets_list = []
        for attr, label in target_points:
            p = self._extract_planet(subject, attr, label)
            if p: planets_list.append(p)

        houses_list = []
        for i, h_attr in enumerate(KERYKEION_HOUSES):
            h_obj = getattr(subject, h_attr, None)
            if h_obj:
                houses_list.append({
                    "house": i + 1,
                    "sign": getattr(h_obj, "sign", ""),
                    "degree": getattr(h_obj, "position", 0.0),
                    "abs_pos": getattr(h_obj, "abs_pos", 0.0)
                })

        # Патч для домов (нужен всегда для корректных оверлеев)
        for p in planets_list:
            if p.get("house") is None:
                p["house"] = get_house_for_degree(p["abs_pos"], houses_list)

        # Южный Узел (нужен всегда для аспектной сетки)
        north_node = next((p for p in planets_list if p["name"] in ["True_North_Lunar_Node", "Mean_North_Lunar_Node"]), None)
        if north_node:
            sn_abs_pos = (north_node["abs_pos"] + 180) % 360
            sn_sign_id = int(sn_abs_pos // 30)
            sn_label = "True_South_Lunar_Node" if inp.node_type == "true" else "Mean_South_Lunar_Node"
            planets_list.append({
                "name": sn_label,
                "sign": SIGNS_SHORT[sn_sign_id], 
                "sign_id": sn_sign_id,
                "degree": sn_abs_pos % 30,
                "abs_pos": sn_abs_pos,
                "house": get_house_for_degree(sn_abs_pos, houses_list) if houses_list else None,
                "is_retro": north_node.get("is_retro", False),
                "speed": north_node.get("speed", 0.0),
                "is_stationary": north_node.get("is_stationary", False)
            })

        # Вычисляем Владыку Рождения (Chart Ruler)
        chart_ruler = None
        if houses_list:
            asc_sign_id = int(houses_list[0]["abs_pos"] // 30)
            chart_ruler = SIGN_RULERS_BY_ID.get(asc_sign_id)

        try:
            cusps, ascmc = swe.houses(subject.julian_day, inp.lat, inp.lon, str(inp.house_system).encode('ascii'))
            vertex_abs = ascmc[3]
            planets_list.append({
                "name": "Vertex",
                "sign": SIGNS_SHORT[int(vertex_abs // 30)], 
                "sign_id": int(vertex_abs // 30),
                "degree": vertex_abs % 30,
                "abs_pos": vertex_abs,
                "house": get_house_for_degree(vertex_abs, houses_list), 
                "is_retro": False, "speed": 0.0, "is_stationary": False
            })

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
                    "sign": SIGNS_SHORT[int(pf_abs // 30)], 
                    "sign_id": int(pf_abs // 30),
                    "degree": pf_abs % 30,
                    "abs_pos": pf_abs,
                    "house": get_house_for_degree(pf_abs, houses_list),
                    "is_retro": False, "speed": 0.0, "is_stationary": False
                })
        except Exception as e:
            print(f"[ENGINE ERROR] Ошибка расчета фиктивных точек: {e}")

        # 🔥 ВСТАВЛЯЕМ УГЛЫ КАРТЫ ОБРАТНО
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
                    "house": None, "is_retro": False, "speed": 0.0, "is_stationary": False
                })

        # Собираем базовый результат
        res = {
            "meta": {
                "engine": "kerykeion_v5",
                "subject": inp.name,
                "datetime": f"{norm_date(inp.date)}T{inp.time}",
                "location": {"lat": inp.lat, "lon": inp.lon},
                "chart_ruler": chart_ruler
            },
            "planets": planets_list,
            "houses": houses_list
        }

        # 🔥 ПРИМЕНЯЕМ СИСТЕМУ КООРДИНАТ / АЙАНАМШУ (Tropical, Sidereal, RA, Draconic, Spring Equinox)
        if inp.coord_system:
            self._apply_coord_system(planets_list, houses_list, subject, inp.coord_system)

        # 🔥 АСПЕКТЫ И ПЛАНЕТНЫЙ ПАРСИНГ
        chart_dump["planets"] = planets_list
        chart_dump["houses"] = houses_list

        # 🔥 ВЫХОДИМ, ЕСЛИ НУЖЕН ТОЛЬКО LITE
        if lite:
            return res

        # === ТЯЖЕЛЫЕ АНАЛИЗАТОРЫ (выполняются только для полной натальной карты) ===
        clean_aspects = calculate_natal_aspects(planets_list, subject.julian_day, custom_orbs=getattr(inp, "custom_orbs", None))
        
        res.update({
            "aspects": clean_aspects,
            "jones_pattern": calculate_jones_pattern(planets_list),
            "dominants": calculate_dominants(planets_list, houses_list, clean_aspects),
            "aspect_patterns": calculate_aspect_patterns(clean_aspects),
            "planet_status": calculate_planet_status(clean_aspects),
            "compensatory": get_compensatory_data(planets_list, clean_aspects),
            "balance": {
                "elements": chart_dump.get("element_distribution"),
                "qualities": chart_dump.get("quality_distribution")
            }
        })
        
        return res

    def _apply_coord_system(self, planets_list: List[Dict[str, Any]], houses_list: List[Dict[str, Any]], subject, coord_system: str):
        if not coord_system or coord_system == "tropical":
            return

        shift = 0.0
        is_ra = (coord_system == "ra")

        SWISSEPH_AYANAMSAS = {
            "fagan": getattr(swe, "SIDM_FAGAN_BRADLEY", 0),
            "lahiri": getattr(swe, "SIDM_LAHIRI", 1),
            "deluce": getattr(swe, "SIDM_DELUCE", 2),
            "raman": getattr(swe, "SIDM_RAMAN", 3),
            "ushashashi": getattr(swe, "SIDM_USHASHASHI", 4),
            "krishnamurti": getattr(swe, "SIDM_KRISHNAMURTI", 5),
            "djwhalkhul": getattr(swe, "SIDM_DJWHAL_KHUL", 6),
            "yukteshwar": getattr(swe, "SIDM_YUKTESHWAR", 7),
            "jnbhasin": getattr(swe, "SIDM_JN_BHASIN", 8),
            "takra": getattr(swe, "SIDM_BABYL_KUGLER1", 9),
            "hipparchos": getattr(swe, "SIDM_HIPPARCHOS", 15),
            "sassanian": getattr(swe, "SIDM_SASSANIAN", 16),
            "j2000": getattr(swe, "SIDM_J2000", 18),
            "j1900": getattr(swe, "SIDM_J1900", 19),
            "b1950": getattr(swe, "SIDM_B1950", 20),
            "citra": getattr(swe, "SIDM_TRUE_CITRA", 27),
            "revati": getattr(swe, "SIDM_TRUE_REVATI", 28),
            "pushya": getattr(swe, "SIDM_TRUE_PUSHIA", 29),
            "galactic_cmid": getattr(swe, "SIDM_GALCENT_MULA_WILHELM", 30),
            "galactic_ccap": getattr(swe, "SIDM_GALCENT_COCHRANE", 31),
            "galactic_iau": getattr(swe, "SIDM_GALEQ_IAU1958", 32),
            "mula": getattr(swe, "SIDM_TRUE_MULA", 35),
            "galactic0": getattr(swe, "SIDM_GALCENT_0SAG", 36),
            "valens": getattr(swe, "SIDM_VALENS_MOON", 37),
            "aldebaran": getattr(swe, "SIDM_ALDEBARAN_15TAU", 14),
            "larry": getattr(swe, "SIDM_LAHIRI", 1),
            "galactic_cgil": getattr(swe, "SIDM_GALCENT_0SAG", 36),
            "galactic_eq": getattr(swe, "SIDM_GALEQ_IAU1958", 32),
            "galactic": getattr(swe, "SIDM_GALCENT_0SAG", 36),
            "galactic_fio": getattr(swe, "SIDM_GALCENT_0SAG", 36),
            "galactic_mid": getattr(swe, "SIDM_GALCENT_MULA_WILHELM", 30),
        }

        if coord_system == "draconic":
            node = next((p for p in planets_list if p["name"] in ["True_North_Lunar_Node", "Mean_North_Lunar_Node"]), None)
            if node:
                shift = node["abs_pos"]
        elif coord_system.startswith("vlastni_"):
            try:
                deg_offset = float(coord_system.replace("vlastni_", ""))
                shift = deg_offset
            except Exception:
                shift = 0.0
        elif coord_system in SWISSEPH_AYANAMSAS:
            sid_mode = SWISSEPH_AYANAMSAS[coord_system]
            try:
                swe.set_sid_mode(sid_mode)
                shift = swe.get_ayanamsa_ut(subject.julian_day)
            except Exception as e:
                print(f"[ENGINE ERROR] SwissEphem ayanamsa error: {e}")
                shift = 24.13

        eps_rad = (23.439 * math.pi) / 180.0

        def transform_pos(orig_pos: float) -> float:
            if is_ra:
                rad = (orig_pos * math.pi) / 180.0
                y = math.sin(rad) * math.cos(eps_rad)
                x = math.cos(rad)
                ra_deg = (math.atan2(y, x) * 180.0) / math.pi
                return (ra_deg % 360 + 360) % 360
            else:
                return (orig_pos - shift + 360) % 360

        for p in planets_list:
            new_pos = transform_pos(p["abs_pos"])
            p["abs_pos"] = new_pos
            p["sign_id"] = int(new_pos // 30) % 12
            p["sign"] = SIGNS_SHORT[p["sign_id"]]
            p["degree"] = new_pos % 30

        for h in houses_list:
            new_pos = transform_pos(h["abs_pos"])
            h["abs_pos"] = new_pos
            h["sign_id"] = int(new_pos // 30) % 12
            h["sign"] = SIGNS_SHORT[h["sign_id"]]
            h["degree"] = new_pos % 30

# === ГЛАВНЫЙ МЕТОД ТРАНЗИТОВ ===
    def transits(self, natal_inp: BirthInput, transit_date: str, extra_house_grids: Optional[Dict[str, List[Dict]]] = None) -> Dict[str, Any]:
        print(f"\n[ENGINE START] Transits for {natal_inp.name} on target date {transit_date}")
        from datetime import datetime, timedelta
        
        natal_data = self.natal(natal_inp)
        natal_houses = natal_data["houses"]
        natal_planets = {p["name"]: p for p in natal_data["planets"]}
        
        # 1. Транзитная карта на СЕГОДНЯ
        y, m, d = parse_ymd(transit_date)
        transit_inp = BirthInput(
            name="Transit", date=f"{y:04d}-{m:02d}-{d:02d}", time="12:00:00",
            tz=natal_inp.tz, lat=natal_inp.lat, lon=natal_inp.lon 
        )
        transit_chart = self.natal(transit_inp)
        
        # 🔥 ВОТ ОНА, ПОТЕРЯННАЯ СТРОЧКА:
        transit_planets = {p["name"]: p for p in transit_chart["planets"]}
        
        # 2. Транзитная карта на ВЧЕРА (для поиска ингрессий)
        t_date_obj = datetime.strptime(transit_date, "%Y-%m-%d")
        y_date_obj = t_date_obj - timedelta(days=1)
        yesterday_inp = BirthInput(
            name="Transit_Yesterday", date=y_date_obj.strftime("%Y-%m-%d"), time="12:00:00",
            tz=natal_inp.tz, lat=natal_inp.lat, lon=natal_inp.lon 
        )
        yesterday_chart = self.natal(yesterday_inp)
        yesterday_planets = {p["name"]: p for p in yesterday_chart["planets"]}
        
        transit_planets_enriched = []
        events = [] 

        # 3. ИЩЕМ ИНГРЕССИИ ПО ВСЕМ СЕТКАМ ДОМОВ
        for p_today in transit_chart["planets"]:
            p_name = p_today["name"]
            
            # --- БАЗОВАЯ ПРОВЕРКА ПО НАТАЛУ ---
            in_house_today = get_house_for_degree(p_today["abs_pos"], natal_houses)
            p_enriched = p_today.copy()
            p_enriched["in_natal_house"] = in_house_today
            
            p_yesterday = yesterday_planets.get(p_name)
            if p_yesterday:
                in_house_yesterday = get_house_for_degree(p_yesterday["abs_pos"], natal_houses)
                
                # Ингрессия в Знак (она общая для всех сеток)
                if p_today.get("sign_id") != p_yesterday.get("sign_id"):
                    events.append({
                        "planet": p_name,
                        "type": "sign_ingress",
                        "from_sign": p_yesterday.get("sign"),
                        "to_sign": p_today.get("sign")
                    })
                
                # Ингрессия в Натальный Дом
                if in_house_today != in_house_yesterday:
                    events.append({
                        "planet": p_name,
                        "type": "natal_house_ingress",
                        "from_house": in_house_yesterday,
                        "to_house": in_house_today
                    })

                # ПРОВЕРКА ИНГРЕССИЙ ДЛЯ СОЛЯРА И ЛУНАРА
                if extra_house_grids:
                    for grid_name, grid_houses in extra_house_grids.items():
                        # Считаем, в каких домах Соляра/Лунара планета была вчера и сегодня
                        grid_house_today = get_house_for_degree(p_today["abs_pos"], grid_houses)
                        grid_house_yesterday = get_house_for_degree(p_yesterday["abs_pos"], grid_houses)
                        
                        if grid_house_today != grid_house_yesterday:
                            events.append({
                                "planet": p_name,
                                "type": f"{grid_name}_house_ingress", 
                                "grid": grid_name,
                                "from_house": grid_house_yesterday,
                                "to_house": grid_house_today
                            })

            transit_planets_enriched.append(p_enriched)

        s_transit = self.build_subject(transit_inp)
        s_natal = self.build_subject(natal_inp)
        raw_aspects = get_synastry_aspects(s_transit, s_natal)
        
        # СЛОВАРИ ДЛЯ МАТЕМАТИКИ И КАТЕГОРИЙ
        ASPECT_ANGLES = {
            "Conjunction": 0, 
            "Sextile": 60, 
            "Square": 90, 
            "Trine": 120, 
            "Opposition": 180,
            # Минорные аспекты:
            "Semisextile": 30,
            "Semisquare": 45,
            "Quintile": 72,
            "Sesquiquadrate": 135,
            "Biquintile": 144,
            "Quincunx": 150
        }
        CATEGORIES = {
            "daily": ["Moon"],
            "short_term": ["Sun", "Mercury", "Venus", "Mars"],
            "long_term": ["Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"],
            "points": ["True_North_Lunar_Node", "Mean_North_Lunar_Node", "True_South_Lunar_Node", "Mean_South_Lunar_Node", "Lilith", "Mean_Lilith", "Chiron", "Ceres", "Pallas", "Juno", "Vesta", "Vertex", "Fortune"]
        }

        transits_categorized = {"daily": [], "short_term": [], "long_term": [], "points": []}

        for a in raw_aspects:
            t_name = a["person1_object"]
            n_name = a["person2_object"]
            aspect_name = a["aspect"]
            orb = a["orb"]

            cat = "points"
            if t_name in CATEGORIES["daily"]: cat = "daily"
            elif t_name in CATEGORIES["short_term"]: cat = "short_term"
            elif t_name in CATEGORIES["long_term"]: cat = "long_term"

            state = "unknown"
            t_p = transit_planets.get(t_name)
            n_p = natal_planets.get(n_name)
            
            if t_p and n_p and aspect_name in ASPECT_ANGLES:
                state = self._get_aspect_state(
                    t_pos=t_p["abs_pos"], 
                    t_speed=t_p["speed"], 
                    n_pos=n_p["abs_pos"], 
                    aspect_angle=ASPECT_ANGLES[aspect_name]
                )

            transits_categorized[cat].append({
                "transit_planet": t_name,
                "natal_planet": n_name,
                "aspect": aspect_name,
                "orb": orb,
                "state": state
            })

        print(f"[ENGINE RESULT] Categorized Aspects: Daily({len(transits_categorized['daily'])}), Short({len(transits_categorized['short_term'])}), Long({len(transits_categorized['long_term'])})")
        
        return {
            "meta": {"type": "transits", "date": transit_date, "target": natal_inp.name},
            "moon_sign": transit_planets.get("Moon", {}).get("sign", ""),
            "transit_planets": transit_planets_enriched,
            "transits": transits_categorized, 
            "events": events 
        }
    
    # === ГЛАВНЫЙ МЕТОД ПРОГНОЗА НА МЕСЯЦ ===
    def monthly_overview(self, natal_inp: BirthInput, year: int, month: int) -> Dict[str, Any]:
        import calendar
        from datetime import datetime, timedelta
        from app.engine.core.utils import get_house_for_degree
        
        print(f"\n[ENGINE START] Monthly Overview for {natal_inp.name} - {year}-{month:02d}")
        
        # 1. Получаем натал пользователя
        natal_data = self.natal(natal_inp)
        natal_houses = natal_data["houses"]
        natal_planets = {p["name"]: p for p in natal_data["planets"]}
        
        num_days = calendar.monthrange(year, month)[1]
        
        ingresses = []
        stations = []
        active_macro_aspects = set() # Используем set, чтобы избежать дубликатов за каждый день
        lunations = []
        
        prev_state = {}
        prev_sun_moon_dist = None
        
        # Медленные планеты и фиктивные точки, задающие фон месяца
        macro_planets = [
            "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto", 
            "True_North_Lunar_Node", "Mean_North_Lunar_Node", "Lilith", "Mean_Lilith"
        ]
        
        ASPECT_ANGLES = {"Conjunction": 0, "Sextile": 60, "Square": 90, "Trine": 120, "Opposition": 180}
        
        # 2. Прокручиваем каждый день месяца
        for day in range(1, num_days + 1):
            date_str = f"{year:04d}-{month:02d}-{day:02d}"
            
            # Болванка транзита на середину дня
            t_inp = BirthInput(
                name="Transit", date=date_str, time="12:00:00",
                tz=natal_inp.tz, lat=natal_inp.lat, lon=natal_inp.lon 
            )
            
            t_chart = self.natal(t_inp)
            t_planets = {p["name"]: p for p in t_chart["planets"]}
            
            # --- АНАЛИЗ ИНГРЕССИЙ И РАЗВОРОТОВ ---
            for p_name, p_data in t_planets.items():
                if p_name not in prev_state:
                    prev_state[p_name] = p_data
                    continue
                
                prev_p = prev_state[p_name]
                
                # Ингрессия в Знак (Игнорируем быструю Луну)
                if p_name != "Moon" and p_data.get("sign_id") != prev_p.get("sign_id"):
                    ingresses.append(f"{date_str}: {p_name} входит в знак {p_data.get('sign')}")
                
                # Ингрессия в Натальный Дом (Игнорируем Луну)
                curr_house = get_house_for_degree(p_data["abs_pos"], natal_houses)
                prev_house = get_house_for_degree(prev_p["abs_pos"], natal_houses)
                if p_name != "Moon" and curr_house != prev_house:
                    ingresses.append(f"{date_str}: {p_name} переходит в {curr_house}-й натальный дом")
                
                # Развороты (Ретроградность / Директность)
                if p_data.get("is_retro") != prev_p.get("is_retro"):
                    direction = "начинает ретроградное движение" if p_data.get("is_retro") else "возвращается в прямое движение"
                    stations.append(f"{date_str}: {p_name} {direction}")
                
                prev_state[p_name] = p_data
                
            # --- АНАЛИЗ МАКРО-АСПЕКТОВ ---
            for t_name in macro_planets:
                t_p = t_planets.get(t_name)
                if not t_p: continue
                
                for n_name, n_p in natal_planets.items():
                    # Смотрим аспекты от медленных только к личным планетам и углам
                    if n_name not in ["Sun", "Moon", "Mercury", "Venus", "Mars", "Ascendant", "Medium_Coeli"]:
                        continue
                        
                    for aspect_name, angle in ASPECT_ANGLES.items():
                        dist = abs(t_p["abs_pos"] - n_p["abs_pos"])
                        if dist > 180: dist = 360 - dist
                        
                        # Если аспект точный (орб меньше 1.5 градуса), фиксируем его
                        orb = abs(dist - angle)
                        if orb <= 1.5: 
                            active_macro_aspects.add(f"Транзитный(ая) {t_name} делает {aspect_name} к натальному(ой) {n_name}")

            # --- АНАЛИЗ ЛУНАЦИЙ (Новолуния / Полнолуния) ---
            sun = t_planets.get("Sun")
            moon = t_planets.get("Moon")
            if sun and moon:
                # Дистанция между Луной и Солнцем (от 0 до 360)
                dist = (moon["abs_pos"] - sun["abs_pos"]) % 360
                
                if prev_sun_moon_dist is not None:
                    # Новолуние (пересечение 0 градусов)
                    if prev_sun_moon_dist > 345 and dist < 15:
                        lunation_house = get_house_for_degree(moon["abs_pos"], natal_houses)
                        lunations.append(f"{date_str}: Новолуние в {moon['sign']} ({lunation_house}-й натальный дом)")
                        
                    # Полнолуние (пересечение 180 градусов)
                    if prev_sun_moon_dist < 180 and dist >= 180:
                        lunation_house = get_house_for_degree(moon["abs_pos"], natal_houses)
                        lunations.append(f"{date_str}: Полнолуние в {moon['sign']} ({lunation_house}-й натальный дом)")
                        
                prev_sun_moon_dist = dist

        return {
            "meta": {"type": "monthly_overview", "year": year, "month": month, "target": natal_inp.name},
            "macro_trends": list(active_macro_aspects), # Превращаем set обратно в list для JSON
            "ingresses": ingresses,
            "stations": stations,
            "lunations": lunations
        }

    # === ГЛАВНЫЙ МЕТОД ГРАФИЧЕСКИХ ЭФЕМЕРИД ===
    def graphical_ephemeris(self, natal_inp: BirthInput, start_date: str, end_date: str, step_days: int = 5) -> Dict[str, Any]:
        import datetime
        from datetime import timedelta

        print(f"\n[ENGINE START] Ephemeris for {natal_inp.name} from {start_date} to {end_date} (step: {step_days} days)")
        
        # 1. Получаем натальную карту (только координаты планет для горизонтальных линий)
        natal_data = self.natal(natal_inp)
        natal_planets = [{"name": p["name"], "abs_pos": p["abs_pos"]} for p in natal_data["planets"]]
        
        # 2. Генерируем таймлайн
        start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d")
        
        ephemeris_data = []
        curr_dt = start_dt
        
        # Точки, которые будем отслеживать (берем из констант движка)
        node_key = "True_North_Lunar_Node" if natal_inp.node_type == "true" else "Mean_North_Lunar_Node"
        target_points = TARGET_POINTS_BASE + [(node_key, node_key)]

        while curr_dt <= end_dt:
            y, m, d = curr_dt.year, curr_dt.month, curr_dt.day
            
            # Создаем болванку для транзитного дня (12:00)
            t_inp = BirthInput(
                name="Transit", date=f"{y:04d}-{m:02d}-{d:02d}", time="12:00:00",
                tz=natal_inp.tz, lat=natal_inp.lat, lon=natal_inp.lon 
            )
            
            # Строим subject напрямую, чтобы не вызывать тяжелые анализаторы
            subject = self.build_subject(t_inp)
            
            day_data = {"date": curr_dt.strftime("%Y-%m-%d")}
            
            # Собираем абсолютные градусы (0-360) всех планет и астероидов на этот день
            for attr, label in target_points:
                p = self._extract_planet(subject, attr, label)
                if p:
                    day_data[p["name"]] = round(p["abs_pos"], 4) 
                    
            ephemeris_data.append(day_data)
            curr_dt += timedelta(days=step_days)
            
        print(f"[ENGINE RESULT] Ephemeris generated: {len(ephemeris_data)} data points")
        
        return {
            "meta": {"type": "ephemeris", "start": start_date, "end": end_date, "step": step_days},
            "natal_planets": natal_planets,
            "ephemeris": ephemeris_data
        }

    # === ГЛАВНЫЙ МЕТОД ГОДОВОЙ ДИАГРАММЫ ГАНТА ТРАНЗИТОВ ===
    def annual_gantt_transits(self, natal_inp: BirthInput, year: int) -> Dict[str, Any]:
        import datetime
        from datetime import timedelta
        from app.engine.core.utils import get_house_for_degree

        print(f"\n[ENGINE START] Annual Gantt Transits for {natal_inp.name} - Year {year}")
        natal_data = self.natal(natal_inp)
        natal_houses = natal_data["houses"]
        natal_planets = {p["name"]: p for p in natal_data["planets"]}

        ASPECT_DEFS = {
            "Conjunction": {"angle": 0, "orb": 4.0, "category": "major", "type": "conjunction"},
            "Opposition": {"angle": 180, "orb": 4.0, "category": "major", "type": "tense"},
            "Square": {"angle": 90, "orb": 3.5, "category": "major", "type": "tense"},
            "Trine": {"angle": 120, "orb": 3.5, "category": "major", "type": "harmonious"},
            "Sextile": {"angle": 60, "orb": 3.0, "category": "major", "type": "harmonious"},
            "Quincunx": {"angle": 150, "orb": 2.0, "category": "minor", "type": "tense"},
            "Semisquare": {"angle": 45, "orb": 1.5, "category": "minor", "type": "tense"},
            "Sesquiquadrate": {"angle": 135, "orb": 1.5, "category": "minor", "type": "tense"},
            "Semisextile": {"angle": 30, "orb": 1.5, "category": "minor", "type": "harmonious"},
            "Quintile": {"angle": 72, "orb": 1.5, "category": "minor", "type": "harmonious"},
            "Biquintile": {"angle": 144, "orb": 1.5, "category": "minor", "type": "harmonious"},
        }

        node_key = "True_North_Lunar_Node" if natal_inp.node_type == "true" else "Mean_North_Lunar_Node"
        transit_planet_keys = [
            "Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", 
            "Uranus", "Neptune", "Pluto", node_key, "Mean_Lilith", "Chiron"
        ]

        start_date = datetime.date(year, 1, 1)
        end_date = datetime.date(year, 12, 31)

        aspect_daily_records = {}

        curr_dt = start_date
        while curr_dt <= end_date:
            date_str = curr_dt.strftime("%Y-%m-%d")
            jd = swe.julday(curr_dt.year, curr_dt.month, curr_dt.day, 12.0)

            for t_name in transit_planet_keys:
                swe_id = SWISSEPH_OBJECTS.get(t_name)
                if swe_id is None:
                    continue

                res, _ = swe.calc_ut(jd, swe_id)
                t_pos = res[0] % 360.0
                is_retro = res[3] < 0

                for n_name, n_p in natal_planets.items():
                    for asp_name, asp_info in ASPECT_DEFS.items():
                        diff = abs(t_pos - n_p["abs_pos"])
                        if diff > 180:
                            diff = 360 - diff

                        orb = abs(diff - asp_info["angle"])
                        if orb <= asp_info["orb"]:
                            key = (t_name, n_name, asp_name)
                            if key not in aspect_daily_records:
                                aspect_daily_records[key] = []
                            house = get_house_for_degree(t_pos, natal_houses)
                            aspect_daily_records[key].append({
                                "date": date_str,
                                "orb": round(orb, 2),
                                "is_retro": is_retro,
                                "house": house
                            })
            curr_dt += timedelta(days=1)

        gantt_items = []
        item_id_counter = 1

        for (t_name, n_name, asp_name), days_data in aspect_daily_records.items():
            if not days_data:
                continue

            asp_info = ASPECT_DEFS[asp_name]
            
            segments = []
            curr_segment = [days_data[0]]

            for i in range(1, len(days_data)):
                prev_d = datetime.datetime.strptime(days_data[i-1]["date"], "%Y-%m-%d").date()
                curr_d = datetime.datetime.strptime(days_data[i]["date"], "%Y-%m-%d").date()
                if (curr_d - prev_d).days <= 3:
                    curr_segment.append(days_data[i])
                else:
                    segments.append(curr_segment)
                    curr_segment = [days_data[i]]
            if curr_segment:
                segments.append(curr_segment)

            for seg in segments:
                start_d = seg[0]["date"]
                end_d = seg[-1]["date"]
                peak_entry = min(seg, key=lambda x: x["orb"])
                peak_d = peak_entry["date"]
                min_orb = peak_entry["orb"]
                house = peak_entry["house"]
                any_retro = any(x["is_retro"] for x in seg)

                gantt_items.append({
                    "id": f"gantt_{item_id_counter}",
                    "transit_planet": t_name,
                    "natal_planet": n_name,
                    "aspect": asp_name,
                    "aspect_category": asp_info["category"],
                    "aspect_type": asp_info["type"],
                    "start_date": start_d,
                    "peak_date": peak_d,
                    "end_date": end_d,
                    "min_orb": min_orb,
                    "house": house,
                    "is_retro": any_retro
                })
                item_id_counter += 1

        return {
            "meta": {"type": "annual_gantt", "year": year, "target": natal_inp.name},
            "year": year,
            "items": gantt_items
        }

    # === ГЛАВНЫЙ МЕТОД ХОРАРА ===
    def horary(self, inp: BirthInput, question: str) -> Dict[str, Any]:
        chart = self.natal(inp)
        
        # Находим Солнце, чтобы понять дневная карта или ночная
        sun = next((p for p in chart["planets"] if p["name"] == "Sun"), None)
        sun_pos = sun["abs_pos"] if sun else 0.0
        
        # Дневная карта, если Солнце в домах над горизонтом (с 7 по 12)
        # Обрати внимание: если дом не определился (None), считаем по умолчанию дневной
        is_day_chart = True
        if sun and sun.get("house"):
            is_day_chart = sun["house"] >= 7

        from app.engine.calculators.dignities_calc import get_essential_dignities
        
        enriched_planets = []
        immune_to_combust = {
            "Sun", "True_North_Lunar_Node", "Mean_North_Lunar_Node", 
            "True_South_Lunar_Node", "Mean_South_Lunar_Node", 
            "Lilith", "Mean_Lilith", "Vertex", "Fortune"
        }

        for p in chart["planets"]:
            p["is_combust"] = False
            p["is_cazimi"] = False
            p["in_via_combusta"] = False
            
            # --- Существующий код сожжения ---
            if p["name"] not in immune_to_combust:
                diff = abs(p["abs_pos"] - sun_pos)
                if diff > 180: 
                    diff = 360 - diff
                
                if diff <= 0.28:
                    p["is_cazimi"] = True    
                elif diff <= 8.5:
                    p["is_combust"] = True   

            if 195.0 <= p["abs_pos"] <= 225.0:
                p["in_via_combusta"] = True
                
            # 🔥 НОВОЕ: Считаем эссенциальные достоинства
            # Считаем только для реальных планет, узлам и фиктивным точкам это не нужно
            if p["name"] in ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]:
                p["dignities"] = get_essential_dignities(p["name"], p["sign_id"], p["degree"], is_day_chart)

            enriched_planets.append(p)
            
        chart["planets"] = enriched_planets
        chart["meta"]["type"] = "horary"
        chart["meta"]["question"] = question
        chart["meta"]["is_day_chart"] = is_day_chart # Отдадим на фронт для справки
        return chart

    # === ГЛАВНЫЙ МЕТОД СИНАСТРИИ (ПОЛНОСТЬЮ ПРОКАЧАННЫЙ) ===
    def synastry(self, p1: BirthInput, p2: BirthInput) -> Dict[str, Any]:
        # Строим полные карты (lite=False), чтобы внутри них отработали расчеты 
        # баланса, доминант, фиктивных точек и углов Asc/Desc/MC/IC для каждого.
        c1 = self.natal(p1, lite=False) 
        c2 = self.natal(p2, lite=False) 
        
        # Рассчитываем взаимные аспекты (включая пересечения с углами карт)
        aspects = get_synastry_aspects(c1["planets"], c2["planets"])
        
        # 🔥 ПОДМЕШИВАЕМ АНАЛИЗАТОР СКОРИНГА СИНАСТРИИ
        synastry_analysis = calculate_synastry_indices(aspects)
        
        # 🔥 ФОРМИРУЕМ СРАВНИТЕЛЬНЫЙ БАЛАНС СТИХИЙ И КАЧЕСТВ ДЛЯ ИИ
        balance_comparison = {
            "elements": {
                "owner": c1.get("balance", {}).get("elements", {}),
                "partner": c2.get("balance", {}).get("elements", {})
            },
            "qualities": {
                "owner": c1.get("balance", {}).get("qualities", {}),
                "partner": c2.get("balance", {}).get("qualities", {})
            }
        }
        
        return {
            "meta": {
                "type": "synastry", 
                "p1": p1.name, 
                "p2": p2.name,
                "owner_chart_ruler": c1["meta"].get("chart_ruler"),
                "partner_chart_ruler": c2["meta"].get("chart_ruler")
            },
            "owner_chart": c1,    
            "partner_chart": c2,  
            "aspects": aspects,
            "overlays": {
                "owner_planets_in_partner_houses": calculate_house_overlays(c1["planets"], c2["houses"]),
                "partner_planets_in_owner_houses": calculate_house_overlays(c2["planets"], c1["houses"])
            },
            "balance_comparison": balance_comparison,
            "synastry_analysis": synastry_analysis # Подмешали наши индексы!
        }
    
    # === ГЛАВНЫЙ МЕТОД КОМПОЗИТА ===
    def composite(self, p1: BirthInput, p2: BirthInput) -> Dict[str, Any]:
        print(f"\n[ENGINE] Расчет Композитной карты: {p1.name} + {p2.name}")
        
        # 1. Получаем полные натальные данные обоих партнеров
        c1 = self.natal(p1, lite=True)
        c2 = self.natal(p2, lite=True)
        
        # 2. Считаем средние точки для планет и домов
        comp_planets = get_composite_planets(c1["planets"], c2["planets"])
        comp_houses = get_composite_houses(c1["houses"], c2["houses"])

        # Считаем баланс
        from app.engine.calculators.composite_calc import calculate_composite_balance
        balance_data = calculate_composite_balance(comp_planets)
        
        # 3. 🔥 ВАЖНО: Композит — это полноценная карта. 
        # Нам нужно рассчитать аспекты ВНУТРИ самого композита.
        # Мы можем переиспользовать наш расчет натальных аспектов!
        from app.engine.calculators.aspects_calc import calculate_natal_aspects
        
        # Используем Julian Day первого партнера как опорный для расчета аспектов (не критично)
        jd_ref = self.build_subject(p1).julian_day
        comp_aspects = calculate_natal_aspects(comp_planets, jd_ref)
        
        # 4. Распределяем планеты композита по домам композита
        from app.engine.core.utils import get_house_for_degree
        for p in comp_planets:
            p["house"] = get_house_for_degree(p["abs_pos"], comp_houses)

        return {
            "meta": {
                "type": "composite",
                "p1": p1.name,
                "p2": p2.name
            },
            "planets": comp_planets,
            "houses": comp_houses,
            "aspects": comp_aspects,
            "balance": balance_data
        }
    
    # === ГЛАВНЫЙ МЕТОД SVG НАТАЛА ===
    def get_natal_svg(self, inp: BirthInput) -> str:
            subject = self.build_subject(inp)
            return build_natal_svg(subject)
    
    # === ГЛАВНЫЙ МЕТОД КОНТЕНТ-ГОРОСКОПА ПО ЗНАКАМ ===
    def content_horoscope(self, sign: str, start_date: str, end_date: str) -> Dict[str, Any]:
        print(f"\n[ENGINE] Генерация контентных событий для {sign} с {start_date} по {end_date}")
        return generate_content_events(sign, start_date, end_date)
    
    # === ГЛАВНЫЙ МЕТОД ЛУННОГО КАЛЕНДАРЯ ===
    def lunar_calendar(self, start_date: str, end_date: str) -> Dict[str, Any]:
        print(f"\n[ENGINE] Генерация Лунного календаря с {start_date} по {end_date}")
        return generate_lunar_calendar(start_date, end_date)
    
    # === ГЛАВНЫЙ МЕТОД ФИРДАРОВ ===
    def firdaria(self, natal_inp: BirthInput, target_date: str) -> Dict[str, Any]:
        print(f"\n[ENGINE] Фирдары для {natal_inp.name} на {target_date}")
        from app.engine.calculators.firdaria_calc import calculate_firdaria
        
        # 1. Получаем натальную карту, чтобы узнать день/ночь и дома
        chart = self.natal(natal_inp)
        
        # 2. Определяем день или ночь
        sun = next((p for p in chart["planets"] if p["name"] == "Sun"), None)
        is_day_chart = True
        if sun and sun.get("house"):
            is_day_chart = sun["house"] >= 7
            
        # 3. Считаем периоды
        firdaria_res = calculate_firdaria(natal_inp.date, target_date, is_day_chart)
        
        # 4. Находим, в каких домах стоят управители периода
        major_house = next((p["house"] for p in chart["planets"] if p["name"] == firdaria_res["major_planet"]), None)
        minor_house = next((p["house"] for p in chart["planets"] if p["name"] == firdaria_res["minor_planet"]), None)
        
        return {
            "meta": {"type": "firdaria", "target_date": target_date, "is_day_chart": is_day_chart},
            "current_period": {
                "major_planet": firdaria_res["major_planet"],
                "major_house": major_house,
                "minor_planet": firdaria_res["minor_planet"],
                "minor_house": minor_house,
                "cycle_age": firdaria_res["cycle_age"]
            }
        }

    # === ГЛАВНЫЙ МЕТОД ДИРЕКЦИЙ ===
    def directions(self, natal_inp: BirthInput, target_date: str, mode: str = "symbolic", orb: float = 1.0) -> Dict[str, Any]:
        print(f"\n[ENGINE] Расчет Дирекций для {natal_inp.name} на {target_date} (режим: {mode}, орб: {orb}°)")
        
        # 1. Получаем натальную карту
        natal_chart = self.natal(natal_inp)
        natal_planets = natal_chart["planets"]
        natal_houses = natal_chart["houses"]
        
        # 2. Вычисляем дугу дирекций и возраст
        arc_degrees, age_in_years = calculate_direction_arc(natal_inp, target_date, mode=mode)
        
        # 3. Рассчитываем дирекционную карту
        directed_chart = calculate_directed_chart(natal_planets, natal_houses, arc_degrees)
        
        # 4. Рассчитываем дирекционные аспекты
        dir_aspects = calculate_directional_aspects(
            directed_planets=directed_chart["planets"],
            directed_houses=directed_chart["houses"],
            natal_planets=natal_planets,
            natal_houses=natal_houses,
            max_orb=orb
        )
        
        return {
            "meta": {
                "type": "directions",
                "mode": mode,
                "target_date": target_date,
                "age_in_years": round(age_in_years, 2),
                "arc_degrees": round(arc_degrees, 4),
                "max_orb": orb,
                "target": natal_inp.name
            },
            "natal_chart": {
                "planets": natal_planets,
                "houses": natal_houses
            },
            "directed_chart": directed_chart,
            "aspects": dir_aspects
        }

# === ГЛАВНЫЙ МЕТОД РЕКТИФИКАЦИИ ===
    def rectify(
        self, 
        natal_inp: BirthInput, 
        events: List[Dict[str, Any]], 
        mode: str = "symbolic", 
        max_orb: float = 1.0,
        start_time: str = "00:00", # 🔥 Принимаем начало окна
        end_time: str = "23:59"     # 🔥 Принимаем конец окна
    ) -> Dict[str, Any]:
        print(f"\n[ENGINE START] Auto-Rectification for {natal_inp.name} (Window: {start_time} - {end_time})")

        noon_inp = BirthInput(
            name=natal_inp.name,
            date=natal_inp.date,
            time="12:00:00",
            tz=natal_inp.tz,
            lat=natal_inp.lat,
            lon=natal_inp.lon,
            house_system=natal_inp.house_system,
            node_type=natal_inp.node_type
        )
        base_chart = self.natal(noon_inp, lite=True)
        natal_planets = base_chart["planets"]
        natal_houses  = base_chart["houses"]

        return calculate_rectification(
            natal_inp=natal_inp,
            natal_planets=natal_planets,
            natal_houses=natal_houses,
            events=events,
            mode=mode,
            max_orb=max_orb,
            start_time=start_time, # 🔥 Прокидываем в калькулятор
            end_time=end_time      # 🔥 Прокидываем в калькулятор
        )

    # === ГЛАВНЫЙ МЕТОД ПОИСКА ЛУЧШИХ ГОРОДОВ (ASTRO-RELOCATION) ===
    def search_best_cities(self, natal_inp: BirthInput, goal_key: str = "career_and_business", top_n: int = 5, country_codes: Optional[List[str]] = None) -> Dict[str, Any]:
        import os
        import json
        from app.engine.analyzers.astro_goals_matrix import get_goal_profile
        from app.engine.geo_engine import GeoAstroEngine
        
        print(f"\n[ENGINE START] Search Best Cities for {natal_inp.name} | Goal: {goal_key} | Countries: {country_codes}")
        
        # 1. Получаем профиль цели из матрицы
        profile = get_goal_profile(goal_key)
        target_planets = profile.get("target_planets", [])
        malefics = profile.get("avoid_hard_aspects_from", [])
        
        # 2. Строим полную натальную карту (lite=False, чтобы получить аспекты)
        natal_chart = self.natal(natal_inp, lite=False)
        natal_aspects = natal_chart.get("aspects", [])
        
        # 3. SAFETY CHECK: Ищем пораженные целевые планеты в натале
        afflicted_planets = set()
        safety_warnings = []
        
        for asp in natal_aspects:
            if asp["type"] in ["square", "opposition"]:  # Нас волнуют только жесткие аспекты
                p1, p2 = asp["p1"], asp["p2"]
                # Если целевая планета поражена малефиком из списка avoid_hard_aspects_from
                if p1 in target_planets and p2 in malefics:
                    afflicted_planets.add(p1)
                    safety_warnings.append(f"Planet {p1} is afflicted by {p2} ({asp['type']}). Lines of {p1} are considered risky and excluded from scoring.")
                elif p2 in target_planets and p1 in malefics:
                    afflicted_planets.add(p2)
                    safety_warnings.append(f"Planet {p2} is afflicted by {p1} ({asp['type']}). Lines of {p2} are considered risky and excluded from scoring.")
                    
        # 4. Загружаем базу городов (используя кэшированный модуль app.geo.cities)
        from app.geo.cities import get_major_cities
        cities = get_major_cities()
        if not cities:
            print("[ENGINE ERROR] Failed to load major_cities from app.geo.cities")
            return {"error": "Cities database not found"}

            
        # 🔥 НОВОЕ: Фильтрация по странам (ускоряет работу в десятки раз)
        if country_codes:
            # Переводим в верхний регистр для надежности
            upper_codes = [code.upper() for code in country_codes]
            cities = [c for c in cities if c.get("country") in upper_codes]
            
            if not cities:
                return {
                    "meta": {
                        "type": "best_cities_search",
                        "error": "No cities found in the specified countries."
                    },
                    "top_cities": []
                }
        
        # 5. Генерируем сырые линии ACG и LS через гео-движок
        geo_engine = GeoAstroEngine()
        acg_data = geo_engine.get_astrocartography_lines(natal_inp)
        ls_data = geo_engine.get_local_space_lines(natal_inp)
        
        # 6. Вызываем первичный скоринг из geo_engine
        raw_cities = geo_engine.calculate_city_scores_combined(
            acg_data=acg_data, 
            ls_data=ls_data, 
            cities=cities, 
            birth_lat=float(natal_inp.lat), 
            birth_lon=float(natal_inp.lon), 
            goal_key=goal_key
        )
        
        # 7. Применяем Safety Check: фильтруем аспекты пораженных планет и пересчитываем баллы
        safe_cities = []
        for city in raw_cities:
            safe_aspects = [asp for asp in city.get("aspects", []) if asp["planet"] not in afflicted_planets]
            
            if not safe_aspects:
                continue 
                
            new_total_score = sum(asp["score"] for asp in safe_aspects)
            
            has_acg = any(a["type"] != "ls" for a in safe_aspects)
            has_ls = any(a["type"] == "ls" for a in safe_aspects)
            is_crossing = has_acg and has_ls
            
            if is_crossing:
                new_total_score = int(new_total_score * 1.2)
                
            city["aspects"] = safe_aspects
            city["total_score"] = new_total_score
            city["is_crossing"] = is_crossing
            
            if new_total_score > 0:
                safe_cities.append(city)
                
        # 8. Сортируем города по убыванию нового чистого балла и берем Топ-N
        safe_cities.sort(key=lambda x: x.get("total_score", 0), reverse=True)
        top_cities = safe_cities[:top_n]
        
        return {
            "meta": {
                "type": "best_cities_search",
                "goal_key": goal_key,
                "goal_name": profile.get("name", ""),
                "target_person": natal_inp.name,
                "safety_warnings": safety_warnings,
                "country_filters": country_codes
            },
            "top_cities": top_cities
        }
