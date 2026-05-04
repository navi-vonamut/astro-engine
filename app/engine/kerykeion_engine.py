from __future__ import annotations
from typing import Any, Dict, List, Optional

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
from app.engine.calculators.electional_calc import generate_daily_inputs, analyze_electional_day
from app.engine.calculators.aspects_calc import calculate_natal_aspects
from app.engine.analyzers.scoring import get_compensatory_data
from app.engine.analyzers.jones_patterns import calculate_jones_pattern
from app.engine.analyzers.dominants import calculate_dominants
from app.engine.analyzers.aspect_patterns import calculate_aspect_patterns
from app.engine.analyzers.planet_status import calculate_planet_status
from app.engine.calculators.content_calc import generate_content_events

class KerykeionEngine:
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
    def solar_return(self, natal_inp: BirthInput, year: int, loc_lat: float, loc_lon: float, loc_tz: str) -> Dict[str, Any]:
        print(f"\n[ENGINE] Соляр для {natal_inp.name}. Год: {year}. Локация: {loc_lat}, {loc_lon}")
        
        # 1. Получаем точную дату и время соляра
        solar_input = calculate_solar_return_input(natal_inp, year, loc_lat, loc_lon, loc_tz)
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
        
        # Достаем самое важное для ИИ - где находится Солярный Асцендент в Натале
        solar_asc_overlay = next((o for o in solar_in_natal_houses if o["planet"] == "Ascendant"), None)
        if solar_asc_overlay:
            solar_chart["meta"]["solar_asc_in_natal_house"] = solar_asc_overlay["in_partner_house"]
            solar_chart["meta"]["solar_asc_in_natal_sign"] = solar_asc_overlay["partner_house_sign"]

        # 5. Добавляем блок наложений в ответ
        solar_chart["overlays"] = {
            "solar_planets_in_natal_houses": solar_in_natal_houses,
            "solar_to_natal_aspects": solar_to_natal_aspects
        }
        
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
    def electional_search(self, start_date: str, end_date: str, lat: float, lon: float, tz: str) -> Dict[str, Any]:
        print(f"\n[ENGINE] Элективный поиск с {start_date} по {end_date} для локации {lat}, {lon}")
        
        daily_inputs = generate_daily_inputs(start_date, end_date, lat, lon, tz)
        
        days_analysis = []
        for inp in daily_inputs:
            # Строим карту на каждый день
            day_chart = self.natal(inp)
            # Извлекаем только самую суть
            day_summary = analyze_electional_day(day_chart)
            days_analysis.append(day_summary)
            
        return {
            "meta": {
                "type": "electional_search",
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

        # 🔥 ВЫХОДИМ, ЕСЛИ НУЖЕН ТОЛЬКО LITE
        if lite:
            return res

        # === ТЯЖЕЛЫЕ АНАЛИЗАТОРЫ (выполняются только для полной натальной карты) ===
        clean_aspects = calculate_natal_aspects(planets_list, subject.julian_day)
        
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

    # === ГЛАВНЫЙ МЕТОД ТРАНЗИТОВ ===
    def transits(self, natal_inp: BirthInput, transit_date: str) -> Dict[str, Any]:
        print(f"\n[ENGINE START] Transits for {natal_inp.name} on target date {transit_date}")
        natal_data = self.natal(natal_inp)
        natal_houses = natal_data["houses"]
        natal_planets = {p["name"]: p for p in natal_data["planets"]}
        
        # Транзитная карта строится на 12:00 (этого достаточно для захвата всех аспектов дня)
        y, m, d = parse_ymd(transit_date)
        transit_inp = BirthInput(
            name="Transit", date=f"{y:04d}-{m:02d}-{d:02d}", time="12:00:00",
            tz=natal_inp.tz, lat=natal_inp.lat, lon=natal_inp.lon 
        )
        
        transit_chart = self.natal(transit_inp)
        transit_planets = {p["name"]: p for p in transit_chart["planets"]}
        
        transit_planets_enriched = []
        for p in transit_chart["planets"]:
            in_house = get_house_for_degree(p["abs_pos"], natal_houses)
            p_enriched = p.copy()
            p_enriched["in_natal_house"] = in_house
            transit_planets_enriched.append(p_enriched)

        s_transit = self.build_subject(transit_inp)
        s_natal = self.build_subject(natal_inp)
        raw_aspects = get_synastry_aspects(s_transit, s_natal)
        
        # 🔥 СЛОВАРИ ДЛЯ МАТЕМАТИКИ И КАТЕГОРИЙ
        ASPECT_ANGLES = {"Conjunction": 0, "Sextile": 60, "Square": 90, "Trine": 120, "Opposition": 180}
        CATEGORIES = {
            "daily": ["Moon"],
            "short_term": ["Sun", "Mercury", "Venus", "Mars"],
            "long_term": ["Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"],
            "points": ["True_North_Lunar_Node", "Mean_North_Lunar_Node", "True_South_Lunar_Node", "Mean_South_Lunar_Node", "Lilith", "Mean_Lilith", "Chiron", "Ceres", "Pallas", "Juno", "Vesta", "Vertex", "Fortune"]
        }

        # 🔥 Добавили 'points'
        transits_categorized = {"daily": [], "short_term": [], "long_term": [], "points": []}

        for a in raw_aspects:
            t_name = a["person1_object"]
            n_name = a["person2_object"]
            aspect_name = a["aspect"]
            orb = a["orb"]

            # Определяем категорию (По умолчанию кидаем в точки, если вдруг прилетело что-то неизвестное)
            cat = "points"
            if t_name in CATEGORIES["daily"]: cat = "daily"
            elif t_name in CATEGORIES["short_term"]: cat = "short_term"
            elif t_name in CATEGORIES["long_term"]: cat = "long_term"

            # Определяем состояние (Сходится/Расходится)
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
            "transits": transits_categorized # 🔥 ТЕПЕРЬ ОТДАЕМ СТРУКТУРИРОВАННЫЙ ОБЪЕКТ
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

    # === ГЛАВНЫЙ МЕТОД ХОРАРА ===
    def horary(self, inp: BirthInput, question: str) -> Dict[str, Any]:
        chart = self.natal(inp)
        sun_pos = next((p["abs_pos"] for p in chart["planets"] if p["name"] == "Sun"), 0.0)
        
        enriched_planets = []
        # Фиктивные точки, которым не страшно сожжение
        immune_to_combust = {
            "Sun", "True_North_Lunar_Node", "Mean_North_Lunar_Node", 
            "True_South_Lunar_Node", "Mean_South_Lunar_Node", 
            "Lilith", "Mean_Lilith", "Vertex", "Fortune"
        }

        for p in chart["planets"]:
            p["is_combust"] = False
            p["is_cazimi"] = False
            p["in_via_combusta"] = False
            
            # 1. Проверка на Сожжение и Казими
            if p["name"] not in immune_to_combust:
                diff = abs(p["abs_pos"] - sun_pos)
                if diff > 180: 
                    diff = 360 - diff
                
                if diff <= 0.28:
                    p["is_cazimi"] = True    # В сердце Солнца (Триумф)
                elif diff <= 8.5:
                    p["is_combust"] = True   # Сожжение (Ослабление)

            # 2. Проверка на Via Combusta (Сожженный путь)
            # От 15° Весов (195°) до 15° Скорпиона (225°)
            if 195.0 <= p["abs_pos"] <= 225.0:
                p["in_via_combusta"] = True

            enriched_planets.append(p)
            
        chart["planets"] = enriched_planets
        chart["meta"]["type"] = "horary"
        chart["meta"]["question"] = question
        return chart

    # === ГЛАВНЫЙ МЕТОД СИНАСТРИИ ===
    def synastry(self, p1: BirthInput, p2: BirthInput) -> Dict[str, Any]:
        c1 = self.natal(p1, lite=True) # 🔥 Lite
        c2 = self.natal(p2, lite=True) # 🔥 Lite
        
        # 🔥 Передаем готовые массивы планет в наш новый калькулятор аспектов
        aspects = get_synastry_aspects(c1["planets"], c2["planets"])
        
        return {
            "meta": {"type": "synastry", "p1": p1.name, "p2": p2.name},
            "owner_chart": c1,    # Опционально: отдаем карты целиком, чтобы фронт мог их нарисовать
            "partner_chart": c2,  
            "aspects": aspects,
            "overlays": {
                "owner_planets_in_partner_houses": calculate_house_overlays(c1["planets"], c2["houses"]),
                "partner_planets_in_owner_houses": calculate_house_overlays(c2["planets"], c1["houses"])
            }
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