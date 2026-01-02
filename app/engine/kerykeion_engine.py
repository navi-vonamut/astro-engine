from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from kerykeion import AstrologicalSubjectFactory, AspectsFactory
from kerykeion.chart_data_factory import ChartDataFactory
import swisseph as swe
import re

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

class KerykeionEngine:
    def build_subject(self, inp: BirthInput):
        y, m, d = _parse_ymd(inp.date)
        hh, mm = _parse_hm(inp.time)
        return AstrologicalSubjectFactory.from_birth_data(
            name=inp.name, year=y, month=m, day=d, hour=hh, minute=mm,
            lng=float(inp.lon), lat=float(inp.lat),
            tz_str=_tz_to_pytz(str(inp.tz)), online=False,
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
            res = swe.calc_ut(jd, pid, 2 | 256) 
            return res[0][3]
        except: return 0.0

    def _extract_planet(self, subject, attr_name: str, display_name: str) -> Optional[Dict[str, Any]]:
        if attr_name == "Mean_Lilith": attr_name = "mean_lilith"
        if attr_name == "True_North_Lunar_Node": attr_name = "true_north_lunar_node"
        point = getattr(subject, attr_name.lower(), None)
        if not point: return None
        real_speed = self._get_swisseph_speed(subject.julian_day, display_name)
        return {
            "name": display_name,
            "sign": getattr(point, "sign", ""),
            "sign_id": getattr(point, "sign_num", 0),
            "degree": getattr(point, "position", 0.0),
            "abs_pos": getattr(point, "abs_pos", 0.0),
            "house": getattr(point, "house", None),
            "is_retro": getattr(point, "retrograde", real_speed < 0),
            "speed": real_speed,
            "is_stationary": abs(real_speed) < 0.05
        }
    
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

    def natal(self, inp: BirthInput) -> Dict[str, Any]:
        subject = self.build_subject(inp)
        chart_data = ChartDataFactory.create_natal_chart_data(subject)
        chart_dump = chart_data.model_dump(mode="json")

        target_points = [
            ("Sun", "Sun"), ("Moon", "Moon"), ("Mercury", "Mercury"), 
            ("Venus", "Venus"), ("Mars", "Mars"), ("Jupiter", "Jupiter"), 
            ("Saturn", "Saturn"), ("Uranus", "Uranus"), ("Neptune", "Neptune"), 
            ("Pluto", "Pluto"), ("Chiron", "Chiron"),
            ("True_North_Lunar_Node", "True Node"), ("Mean_Lilith", "Lilith")
        ]
        planets_list = []
        for attr, label in target_points:
            p = self._extract_planet(subject, attr, label)
            if p: planets_list.append(p)

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

        clean_aspects = []
        for a in chart_dump.get("aspects", []):
            clean_aspects.append({
                "p1": a.get("p1_name"),
                "p2": a.get("p2_name"),
                "type": a.get("aspect"),
                "orb": round(a.get("orbit", 0), 4),
                "is_applying": a.get("aspect_movement") == "Applying",
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

        # 1. Белый список планет (Игнорируем дома: First House и т.д.)
        PLANET_WHITELIST = {
            "Sun", "Moon", "Mercury", "Venus", "Mars", 
            "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto",
            "Chiron", "True Node", "Lilith"
        }
        
        # 2. Только мажорные аспекты
        ALLOWED_ASPECTS = {"conjunction", "opposition", "square", "trine", "sextile"}
        
        aspects = []
        for a in res.aspects:
            d = a.model_dump(mode="json")
            
            p1_n = d.get("p1_name", "")
            p2_n = d.get("p2_name", "")
            raw_asp = d.get("aspect_name") or d.get("aspect") or ""
            asp_lower = raw_asp.lower()
            orb = float(d.get("orb") or 0.0)

            # ФИЛЬТР: Только планеты из белого списка
            # Если хоть один участник - не планета (например, House), пропускаем
            if p1_n not in PLANET_WHITELIST or p2_n not in PLANET_WHITELIST:
                continue

            # ФИЛЬТР: Только мажорные аспекты
            if asp_lower not in ALLOWED_ASPECTS:
                continue

            # ФИЛЬТР: Умные Орбисы
            limit = 3.0 # Базовый строгий
            
            if "Moon" in p1_n:
                limit = 8.0  
            elif "Sun" in p1_n:
                limit = 6.0
            elif p1_n in ["Mercury", "Venus", "Mars"]:
                limit = 5.0
            elif p1_n in ["Jupiter", "Saturn"]:
                limit = 4.0
            
            # Фиктивные точки строго
            if any(x in p1_n for x in ["Node", "Lilith", "Chiron"]):
                limit = 1.5

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

        print(f"[ENGINE RESULT] Final Aspect Count: {len(transit_aspects)} (Strict Filtered)")
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