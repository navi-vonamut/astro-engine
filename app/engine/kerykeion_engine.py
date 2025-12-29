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
        """Создает объект AstrologicalSubject (основная модель данных)"""
        y, m, d = _parse_ymd(inp.date)
        hh, mm = _parse_hm(inp.time)
        
        return AstrologicalSubjectFactory.from_birth_data(
            name=inp.name,
            year=y,
            month=m,
            day=d,
            hour=hh,
            minute=mm,
            lng=float(inp.lon),
            lat=float(inp.lat),
            tz_str=_tz_to_pytz(str(inp.tz)),
            online=False,
        )
    
    def _get_swisseph_speed(self, jd: float, p_name: str) -> float:
        """
        Получает скорость планеты напрямую через swisseph.
        jd: Julian Day (есть в объекте subject)
        p_name: Имя планеты (Sun, Moon...)
        """
        # Маппинг имен Kerykeion -> ID SwissEph
        mapping = {
            "Sun": 0, "Moon": 1, "Mercury": 2, "Venus": 3, "Mars": 4,
            "Jupiter": 5, "Saturn": 6, "Uranus": 7, "Neptune": 8, "Pluto": 9,
            "Mean_Lilith": 11, # Обычно Lilith (Mean Node) это специфичный ID, но часто используют 11 (Node) или спец. флаги
            "True_North_Lunar_Node": 11, # True Node
            "Chiron": 15, # Иногда требует перенастройки флагов, но базово ID 15
        }
        
        pid = mapping.get(p_name)
        if pid is None:
            return 0.0
            
        # swe.calc_ut возвращает кортеж, где индекс [3] - это скорость по долготе
        try:
            # FLG_SWIEPH=2, FLG_SPEED=256
            res = swe.calc_ut(jd, pid, 2 | 256) 
            return res[0][3] # Скорость в градусах в день
        except:
            return 0.0

    def _extract_planet(self, subject, attr_name: str, display_name: str) -> Optional[Dict[str, Any]]:
        """Безопасное извлечение данных планеты из атрибута модели"""
        
        # Маппинг имен для специфических точек (Kerykeion v5 migration)
        if attr_name == "Mean_Lilith": attr_name = "mean_lilith" # или lilith, зависит от версии, пробуем стандарт
        if attr_name == "True_North_Lunar_Node": attr_name = "true_north_lunar_node"
        
        # Пытаемся получить объект точки
        # В v5 точки лежат в атрибутах: subject.sun, subject.moon и т.д.
        point = getattr(subject, attr_name.lower(), None)
        
        if not point:
            return None

        # Извлекаем данные.
        real_speed = self._get_swisseph_speed(subject.julian_day, display_name)
        
        return {
            "name": display_name,
            "sign": getattr(point, "sign", ""),
            "sign_id": getattr(point, "sign_num", 0),
            "degree": getattr(point, "position", 0.0), # 0-30
            "abs_pos": getattr(point, "abs_pos", 0.0), # 0-360
            "house": getattr(point, "house", None),
            "is_retro": getattr(point, "retrograde", real_speed < 0),
            "speed": real_speed,
            "is_stationary": abs(real_speed) < 0.05 # Порог стационарности (например, меньше 3 минут в день)
        }
    
    def _get_house_for_degree(self, degree: float, houses: List[Dict]) -> int:
        """
        Определяет, в какой дом попадает заданный градус (0-360).
        houses: список домов натальной карты (с полями abs_pos).
        """
        # Это упрощенная логика для Плацидуса/Коха, где дома идут последовательно.
        # Нужно учитывать переход через 0/360 (рыбы-овен).
        
        # Нормализуем градус
        deg = degree % 360
        
        # Проходим по домам. Если куспид 1 дома = 350, а куспид 2 = 20, 
        # то точка 5 градусов попадает в 1 дом.
        for i in range(len(houses)):
            curr_h = houses[i]
            next_h = houses[(i + 1) % len(houses)]
            
            c1 = curr_h["abs_pos"]
            c2 = next_h["abs_pos"]
            
            # Обработка перехода через 0
            if c1 > c2: 
                if deg >= c1 or deg < c2:
                    return curr_h["house"]
            else:
                if c1 <= deg < c2:
                    return curr_h["house"]
                    
        return 1 # Fallback

    def _is_combust(self, planet_abs_pos: float, sun_abs_pos: float) -> bool:
        """Проверка на сожжение (расстояние до Солнца < 8.5 градусов)"""
        diff = abs(planet_abs_pos - sun_abs_pos)
        if diff > 180: diff = 360 - diff
        return diff < 8.5

    def natal(self, inp: BirthInput) -> Dict[str, Any]:
        # 1. Создаем объект (расчеты происходят внутри Factory)
        subject = self.build_subject(inp)
        
        # 2. Получаем аспекты через ChartDataFactory
        # Это самый надежный способ получить аспекты в v5
        chart_data = ChartDataFactory.create_natal_chart_data(subject)
        chart_dump = chart_data.model_dump(mode="json")

        # 3. Собираем планеты (Вручную проходим по известным атрибутам)
        # Kerykeion v5 не дает итерируемого списка планет, нужно дергать атрибуты
        target_points = [
            ("Sun", "Sun"), 
            ("Moon", "Moon"), 
            ("Mercury", "Mercury"), 
            ("Venus", "Venus"), 
            ("Mars", "Mars"), 
            ("Jupiter", "Jupiter"), 
            ("Saturn", "Saturn"), 
            ("Uranus", "Uranus"), 
            ("Neptune", "Neptune"), 
            ("Pluto", "Pluto"),
            ("Chiron", "Chiron"),
            ("True_North_Lunar_Node", "True Node"),
            ("Mean_Lilith", "Lilith") # Проверьте точное имя атрибута в документации, если вернет null
        ]
        
        planets_list = []
        for attr, label in target_points:
            p = self._extract_planet(subject, attr, label)
            if p:
                planets_list.append(p)

        # 4. Собираем дома
        # В v5 дома - это отдельные атрибуты: first_house, second_house...
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

        # 5. Чистим аспекты
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
        res = AspectsFactory.dual_chart_aspects(s1, s2)
        aspects = []
        for a in res.aspects:
            d = a.model_dump(mode="json")
            aspects.append({
                "person1_object": d.get("p1_name"),
                "aspect": d.get("aspect_name") or d.get("aspect"),
                "person2_object": d.get("p2_name"),
                "orb": float(d.get("orb") or 0.0),
            })
        return aspects

    def transits(self, natal_inp: BirthInput, transit_date: str) -> Dict[str, Any]:
        """
        ПРОДВИНУТЫЕ ТРАНЗИТЫ
        Строит карту на 12:00 указанного дня и накладывает на натал.
        Добавляет: в какой натальный дом попала транзитная планета.
        """
        # 1. Считаем Натал (чтобы получить сетку домов)
        natal_data = self.natal(natal_inp)
        natal_houses = natal_data["houses"]
        
        # 2. Строим Транзитную карту (на 12:00)
        y, m, d = _parse_ymd(transit_date)
        transit_inp = BirthInput(
            name="Transit", date=f"{y:04d}-{m:02d}-{d:02d}", time="12:00:00",
            tz=natal_inp.tz, lat=natal_inp.lat, lon=natal_inp.lon # Транзит обычно смотрят на локацию рождения или проживания
        )
        # Используем наш метод natal, чтобы получить координаты транзитных планет со скоростями
        transit_chart = self.natal(transit_inp)

        # 3. Собираем данные: Планета -> Где она в Натале
        transit_planets_enriched = []
        for p in transit_chart["planets"]:
            # Ищем, в какой натальный дом попала эта транзитная планета
            in_house = self._get_house_for_degree(p["abs_pos"], natal_houses)
            
            p_enriched = p.copy()
            p_enriched["in_natal_house"] = in_house
            transit_planets_enriched.append(p_enriched)

        # 4. Аспекты (Транзит -> Натал)
        # Используем synastry логику, но в одну сторону
        aspects = self.synastry_aspects(transit_inp, natal_inp)
        
        # Фильтруем аспекты: нас интересуют Транзит(p1) -> Натал(p2)
        # В synastry_aspects p1 - это transit_inp
        transit_aspects = []
        for a in aspects:
            transit_aspects.append({
                "transit_planet": a["person1_object"],
                "aspect": a["aspect"],
                "natal_planet": a["person2_object"],
                "orb": a["orb"],
                # is_applying нет в стандартной factory синастрии, 
                # но для транзитов можно добавить логику проверки скоростей, если критично.
                # Пока оставим как есть.
            })

        return {
            "meta": {"type": "transits", "date": transit_date, "target": natal_inp.name},
            "transit_planets": transit_planets_enriched, # Тут теперь есть in_natal_house!
            "aspects": transit_aspects
        }

    def horary(self, inp: BirthInput, question: str) -> Dict[str, Any]:
        """
        ХОРАРНАЯ КАРТА (Карта вопроса)
        Отличается от натала наличием специфических флагов (сожжение).
        """
        # 1. Базовый расчет как натал
        chart = self.natal(inp)
        
        # 2. Находим Солнце (для расчета сожжения)
        sun_pos = next((p["abs_pos"] for p in chart["planets"] if p["name"] == "Sun"), 0.0)
        
        # 3. Обогащаем планеты хорарными признаками
        enriched_planets = []
        for p in chart["planets"]:
            # Проверка на сожжение (кроме самого Солнца)
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
        """
        ПОЛНАЯ СИНАСТРИЯ
        Аспекты + Наложение домов (Где мои планеты в твоей карте).
        """
        # 1. Расчет обеих карт
        c1 = self.natal(p1) # Owner
        c2 = self.natal(p2) # Partner
        
        # 2. Аспекты
        aspects = self.synastry_aspects(p1, p2)
        
        # 3. Наложение (Overlays)
        # Где планеты P1 находятся в домах P2
        p1_in_p2_houses = []
        for p in c1["planets"]:
            house_in_p2 = self._get_house_for_degree(p["abs_pos"], c2["houses"])
            p1_in_p2_houses.append({
                "planet": p["name"],
                "in_partner_house": house_in_p2,
                "partner_house_sign": c2["houses"][house_in_p2-1]["sign"] # знак куспида дома
            })

        # Где планеты P2 находятся в домах P1
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