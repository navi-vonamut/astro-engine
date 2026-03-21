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
from app.engine.calculators.solar_calc import calculate_solar_return_input
from app.engine.calculators.aspects_calc import calculate_natal_aspects
from app.engine.analyzers.scoring import get_compensatory_data
from app.engine.analyzers.jones_patterns import calculate_jones_pattern
from app.engine.analyzers.dominants import calculate_dominants
from app.engine.analyzers.aspect_patterns import calculate_aspect_patterns
from app.engine.analyzers.planet_status import calculate_planet_status

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

    # === ГЛАВНЫЙ МЕТОД СОЛЯРА ===
    def solar_return(self, natal_inp: BirthInput, year: int, loc_lat: float, loc_lon: float, loc_tz: str) -> Dict[str, Any]:
        print(f"\n[ENGINE] Соляр для {natal_inp.name}. Год: {year}. Локация: {loc_lat}, {loc_lon}")
        solar_input = calculate_solar_return_input(natal_inp, year, loc_lat, loc_lon, loc_tz)
        print(f"[ENGINE] Дата Соляра (Local): {solar_input.date} {solar_input.time}")
        chart = self.natal(solar_input)
        chart["meta"]["type"] = "solar_return"
        chart["meta"]["solar_year"] = year
        chart["meta"]["location_name"] = f"{loc_lat}, {loc_lon}" 
        return chart

    # === ГЛАВНЫЙ МЕТОД НАТАЛА ===
    def natal(self, inp: BirthInput) -> Dict[str, Any]:
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

        # Патч для домов
        for p in planets_list:
            if p.get("house") is None:
                p["house"] = get_house_for_degree(p["abs_pos"], houses_list)

        # Высчитываем Южный Узел
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

        # Фиктивные точки
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
                "is_retro": False,
                "speed": 0.0,
                "is_stationary": False
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
                    "is_retro": False,
                    "speed": 0.0,
                    "is_stationary": False
                })
        except Exception as e:
            print(f"[ENGINE ERROR] Ошибка расчета фиктивных точек: {e}")

        # Углы карты
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

        # === ОБОГАЩЕНИЕ УПРАВИТЕЛЯМИ (ДИСПОЗИТОРЫ И АЛЬМУТЕНЫ) ===
        
        # 1. Назначаем управителей домам (Альмутены)
        for h in houses_list:
            sign_id = int(h["abs_pos"] // 30)
            h["ruler"] = SIGN_RULERS_BY_ID.get(sign_id)
            
        # 2. Назначаем диспозиторов планетам
        for p in planets_list:
            if "abs_pos" in p:
                sign_id = int(p["abs_pos"] // 30)
                p["dispositor"] = SIGN_RULERS_BY_ID.get(sign_id)
                
        # 3. Вычисляем Владыку Рождения (Chart Ruler) - управителя Асцендента
        chart_ruler = None
        if houses_list:
            asc_sign_id = int(houses_list[0]["abs_pos"] // 30)
            chart_ruler = SIGN_RULERS_BY_ID.get(asc_sign_id)
            
        # ==========================================================

        # Калькуляторы и анализаторы
        clean_aspects = calculate_natal_aspects(planets_list, subject.julian_day)
        jones_pattern_data = calculate_jones_pattern(planets_list)
        dominants_data = calculate_dominants(planets_list, houses_list, clean_aspects)
        aspect_patterns_data = calculate_aspect_patterns(clean_aspects)
        planet_status_data = calculate_planet_status(clean_aspects)
        compensatory = get_compensatory_data(planets_list, clean_aspects)

        return {
            "meta": {
                "engine": "kerykeion_v5",
                "subject": inp.name,
                "datetime": f"{norm_date(inp.date)}T{inp.time}",
                "location": {"lat": inp.lat, "lon": inp.lon},
                "chart_ruler": chart_ruler
            },
            "planets": planets_list,
            "houses": houses_list,
            "aspects": clean_aspects,
            "jones_pattern": jones_pattern_data,
            "dominants": dominants_data,
            "aspect_patterns": aspect_patterns_data,
            "planet_status": planet_status_data,
            "compensatory": compensatory,
            "balance": {
                "elements": chart_dump.get("element_distribution"),
                "qualities": chart_dump.get("quality_distribution")
            }
        }

    # === ГЛАВНЫЙ МЕТОД ТРАНЗИТОВ ===
    def transits(self, natal_inp: BirthInput, transit_date: str) -> Dict[str, Any]:
        print(f"\n[ENGINE START] Transits for {natal_inp.name} on target date {transit_date}")
        natal_data = self.natal(natal_inp)
        natal_houses = natal_data["houses"]
        
        y, m, d = parse_ymd(transit_date)
        transit_inp = BirthInput(
            name="Transit", date=f"{y:04d}-{m:02d}-{d:02d}", time="12:00:00",
            tz=natal_inp.tz, lat=natal_inp.lat, lon=natal_inp.lon 
        )
        
        transit_chart = self.natal(transit_inp)
        transit_planets_enriched = []
        for p in transit_chart["planets"]:
            in_house = get_house_for_degree(p["abs_pos"], natal_houses)
            p_enriched = p.copy()
            p_enriched["in_natal_house"] = in_house
            transit_planets_enriched.append(p_enriched)

        s_transit = self.build_subject(transit_inp)
        s_natal = self.build_subject(natal_inp)
        aspects = get_synastry_aspects(s_transit, s_natal)
        
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

    # === ГЛАВНЫЙ МЕТОД ХОРАРА ===
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

    # === ГЛАВНЫЙ МЕТОД СИНАСТРИИ ===
    def synastry(self, p1: BirthInput, p2: BirthInput) -> Dict[str, Any]:
        c1 = self.natal(p1)
        c2 = self.natal(p2)
        
        s1 = self.build_subject(p1)
        s2 = self.build_subject(p2)
        aspects = get_synastry_aspects(s1, s2)
        
        return {
            "meta": {"type": "synastry", "p1": p1.name, "p2": p2.name},
            "aspects": aspects,
            "overlays": {
                "owner_planets_in_partner_houses": calculate_house_overlays(c1["planets"], c2["houses"]),
                "partner_planets_in_owner_houses": calculate_house_overlays(c2["planets"], c1["houses"])
            }
        }
    
    # === ГЛАВНЫЙ МЕТОД SVG НАТАЛА ===
    def get_natal_svg(self, inp: BirthInput) -> str:
            subject = self.build_subject(inp)
            return build_natal_svg(subject)