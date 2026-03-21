import swisseph as swe
import math
import numpy as np
from typing import Dict, Any

from app.engine.core.models import BirthInput
from kerykeion import AstrologicalSubjectFactory
from app.engine.core.utils import measure_time, get_utc_jd_from_input, tz_to_pytz, parse_ymd, parse_hm
from app.engine.core.constants import SWISSEPH_OBJECTS
from app.engine.core.geo_math import (
    to_dms, normalize_lon, generate_geodesic_path, 
    calculate_bearing, interpolate_dateline
)

class GeoAstroEngine:

    # ==========================================
    # 1. АСТРОКАРТОГРАФИЯ (ACG)
    # ==========================================
    @measure_time
    def get_astrocartography_lines(self, inp: BirthInput) -> Dict[str, Any]:
        result = {}
        jd = get_utc_jd_from_input(inp)
        gst_deg = swe.sidtime(jd) * 15.0
        MAX_MERCATOR_LAT = 85.0
        base_lats = np.arange(-MAX_MERCATOR_LAT, MAX_MERCATOR_LAT + 1, 1.0).tolist()
        
        for p_name, p_id in SWISSEPH_OBJECTS.items():
            try:
                res, _ = swe.calc_ut(jd, p_id, swe.FLG_SWIEPH | swe.FLG_EQUATORIAL)
            except Exception: continue
            ra, decl = res[0], res[1]
            lines = {"MC": [], "IC": [], "ASC": [], "DSC": [], "Zenith": []}
            
            lon_mc = normalize_lon(ra - gst_deg)
            lon_ic = normalize_lon(ra - gst_deg + 180.0)
            mc_pts, ic_pts = [], []
            for lat in range(int(-MAX_MERCATOR_LAT), int(MAX_MERCATOR_LAT) + 1, 5): 
                mc_pts.append([float(lat), round(lon_mc, 3)])
                ic_pts.append([float(lat), round(lon_ic, 3)])
            
            lines["MC"] = [mc_pts]; lines["IC"] = [ic_pts]; lines["Zenith"] = [round(decl, 3), round(lon_mc, 3)]
            
            asc_segments, dsc_segments = [], []
            curr_asc, curr_dsc = [], []
            prev_asc, prev_dsc = None, None
            
            limit_real = 90.0 - abs(decl)
            limit_map = min(limit_real, MAX_MERCATOR_LAT)
            lats = [lat for lat in base_lats if abs(lat) < (limit_map - 2.0)]
            
            if limit_real < MAX_MERCATOR_LAT:
                steps = [2.0, 1.0, 0.5, 0.2, 0.1, 0.05, 0.01]
                for s in steps:
                    if (limit_map - s) > lats[-1]: lats.extend([limit_map - s, -limit_map + s])
                lats.extend([limit_map, -limit_map])
            else: 
                lats.extend([MAX_MERCATOR_LAT, -MAX_MERCATOR_LAT])
                
            lats = sorted(list(set(lats)))
            decl_rad = math.radians(decl)
            tan_decl = math.tan(decl_rad)
            
            for lat in lats:
                try: 
                    tan_lat = math.tan(math.radians(lat))
                    cos_h = -tan_lat * tan_decl
                except: continue
                
                if cos_h > 1.0: cos_h = 1.0
                elif cos_h < -1.0: cos_h = -1.0
                
                h_deg = math.degrees(math.acos(cos_h))
                
                # Линия ASC
                lon_asc = normalize_lon((ra - h_deg) - gst_deg)
                if prev_asc is not None:
                    p_lat, p_lon = prev_asc; diff = lon_asc - p_lon
                    if abs(diff) > 180:
                        pt_end, pt_start = interpolate_dateline(p_lat, p_lon, lat, lon_asc)
                        if pt_end: curr_asc.append(pt_end); asc_segments.append(curr_asc); curr_asc = [pt_start]
                    elif abs(lat) >= (MAX_MERCATOR_LAT - 0.1) and abs(diff) > 20: 
                        asc_segments.append(curr_asc); curr_asc = []
                curr_asc.append([lat, round(lon_asc, 3)]); prev_asc = (lat, lon_asc)
                
                # Линия DSC
                lon_dsc = normalize_lon((ra + h_deg) - gst_deg)
                if prev_dsc is not None:
                    p_lat, p_lon = prev_dsc; diff = lon_dsc - p_lon
                    if abs(diff) > 180:
                        pt_end, pt_start = interpolate_dateline(p_lat, p_lon, lat, lon_dsc)
                        if pt_end: curr_dsc.append(pt_end); dsc_segments.append(curr_dsc); curr_dsc = [pt_start]
                    elif abs(lat) >= (MAX_MERCATOR_LAT - 0.1) and abs(diff) > 20: 
                        dsc_segments.append(curr_dsc); curr_dsc = []
                curr_dsc.append([lat, round(lon_dsc, 3)]); prev_dsc = (lat, lon_dsc)
                
            if curr_asc: asc_segments.append(curr_asc)
            if curr_dsc: dsc_segments.append(curr_dsc)
            lines["ASC"] = asc_segments; lines["DSC"] = dsc_segments
            result[p_name] = lines
        return result

    # ==========================================
    # 2. LOCAL SPACE
    # ==========================================
    @measure_time
    def get_local_space_lines(self, inp: BirthInput) -> Dict[str, Any]:
        jd = get_utc_jd_from_input(inp)
        swe.set_topo(float(inp.lon), float(inp.lat), 0.0)
        observer_coords = (float(inp.lon), float(inp.lat), 0.0)
        
        lines = {}

        # Углы
        try:
            cusps, ascmc = swe.houses(jd, float(inp.lat), float(inp.lon), b'P')
            asc_deg, mc_deg = ascmc[0], ascmc[1]
            ecl_res = swe.calc_ut(jd, swe.ECL_NUT, 0)
            true_obliquity = ecl_res[0][1]

            angles_map = {'Ascendant': asc_deg, 'Medium_Coeli': mc_deg}
            for name, lon_deg in angles_map.items():
                t_res = swe.cotrans((lon_deg, 0.0, 1.0), -true_obliquity)
                ra, dec = t_res[0], t_res[1]
                
                res_az = swe.azalt(jd, swe.EQU2HOR, observer_coords, 0.0, 0.0, (ra, dec, 1.0))
                az_north = (res_az[0] + 180.0) % 360.0

                forward = generate_geodesic_path(inp.lat, inp.lon, az_north, 20000)
                reverse = generate_geodesic_path(inp.lat, inp.lon, (az_north + 180) % 360, 20000)

                lines[name] = {"azimuth": round(az_north, 4), "forward_paths": forward, "reverse_paths": reverse}
        except Exception as e: print(f"❌ Error Angles: {e}")

        # Планеты
        for p_name, p_id in SWISSEPH_OBJECTS.items():
            try:
                flags = swe.FLG_SWIEPH | swe.FLG_TOPOCTR | swe.FLG_EQUATORIAL
                res_pos = swe.calc_ut(jd, p_id, flags)
                planet_coords = tuple(res_pos[0])[:3]
                
                res_az = swe.azalt(jd, swe.EQU2HOR, observer_coords, 0.0, 0.0, planet_coords)
                az_north = (res_az[0] + 180.0) % 360.0

            except Exception as e: continue

            forward = generate_geodesic_path(inp.lat, inp.lon, az_north, 20000)
            reverse = generate_geodesic_path(inp.lat, inp.lon, (az_north + 180) % 360, 20000)

            lines[p_name] = {"azimuth": round(az_north, 4), "forward_paths": forward, "reverse_paths": reverse}

        return lines

    # ==========================================
    # 3. COMBINED SCORING 
    # ==========================================
    @measure_time
    def calculate_city_scores_combined(self, acg_data, ls_data, cities, birth_lat, birth_lon):
        MAX_ORB_KM = 700.0; R_EARTH = 6371.0; LS_ORB_DEGREES = 3.0 
        
        line_points, meta_store, line_meta_indices = [], [], []
        for planet, data in acg_data.items():
            for angle in ['MC', 'IC', 'ASC', 'DSC', 'Zenith']:
                if angle == 'Zenith':
                     if data.get('Zenith'):
                        line_points.append(data['Zenith']); meta_store.append({'planet': planet, 'angle': 'Zenith', 'type': 'zenith'}); line_meta_indices.append(len(meta_store)-1)
                else:
                    for segment in data.get(angle, []):
                        for pt in segment:
                            line_points.append(pt); meta_store.append({'planet': planet, 'angle': angle, 'type': 'line'}); line_meta_indices.append(len(meta_store)-1)

        if not cities: return []
        city_coords = np.array([[c['lat'], c['lon']] for c in cities], dtype=np.float32)
        city_rads = np.radians(city_coords)
        
        acg_results = {}
        if line_points:
            line_points_arr = np.array(line_points, dtype=np.float32)
            line_rads = np.radians(line_points_arr)
            lat1, lon1 = city_rads[:, 0:1], city_rads[:, 1:2]
            lat2, lon2 = line_rads[:, 0], line_rads[:, 1]
            dlat, dlon = lat2 - lat1, lon2 - lon1
            a = np.sin(dlat/2.0)**2 + np.cos(lat1)*np.cos(lat2)*np.sin(dlon/2.0)**2
            c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - np.clip(a, 0, 1)))
            distances_km = R_EARTH * c 
            valid_indices = np.where(distances_km <= MAX_ORB_KM)
            for city_idx, point_idx in zip(valid_indices[0], valid_indices[1]):
                dist = float(distances_km[city_idx, point_idx])
                meta = meta_store[line_meta_indices[point_idx]]
                max_score = 150 if meta['type'] == 'zenith' else 100
                score_val = max_score * (1 - (dist / MAX_ORB_KM))
                aspect = {"planet": meta['planet'], "angle": meta['angle'], "distance_km": int(dist), "score": int(score_val), "type": meta['type']}
                if city_idx not in acg_results: acg_results[city_idx] = []
                existing = next((x for x in acg_results[city_idx] if x['planet'] == aspect['planet'] and x['angle'] == aspect['angle']), None)
                if existing:
                    if aspect['score'] > existing['score']: existing['distance_km'] = aspect['distance_km']; existing['score'] = aspect['score']
                else: acg_results[city_idx].append(aspect)

        final_cities = []
        for i, city in enumerate(cities):
            current_aspects = acg_results.get(i, [])
            bearing_to_city = calculate_bearing(birth_lat, birth_lon, city['lat'], city['lon'])
            ls_aspects = []
            if ls_data:
                for planet, p_data in ls_data.items():
                    planet_az = p_data['azimuth']
                    
                    diff_fwd = abs(bearing_to_city - planet_az)
                    if diff_fwd > 180: diff_fwd = 360 - diff_fwd
                    
                    planet_az_rev = (planet_az + 180.0) % 360.0
                    diff_rev = abs(bearing_to_city - planet_az_rev)
                    if diff_rev > 180: diff_rev = 360 - diff_rev

                    if diff_fwd <= LS_ORB_DEGREES:
                        score = 50 * (1 - diff_fwd/LS_ORB_DEGREES)
                        ls_aspects.append({"planet": planet, "angle": "Local Space", "distance_km": 0, "score": int(score), "type": "ls"})
                    elif diff_rev <= LS_ORB_DEGREES:
                        score = 50 * (1 - diff_rev/LS_ORB_DEGREES)
                        ls_aspects.append({"planet": planet, "angle": "Local Space (Оппозиция)", "distance_km": 0, "score": int(score), "type": "ls"})
            
            has_acg = len(current_aspects) > 0; has_ls = len(ls_aspects) > 0; is_crossing = has_acg and has_ls
            all_aspects = current_aspects + ls_aspects
            all_aspects.sort(key=lambda x: x['score'], reverse=True)
            if all_aspects:
                c_copy = city.copy(); c_copy['aspects'] = all_aspects; c_copy['is_crossing'] = is_crossing
                final_cities.append(c_copy)
                
        return final_cities

    def get_relocation_raw_data(self, inp: BirthInput, target_lat: float, target_lon: float, city_name: str) -> Dict[str, Any]:
        jd = get_utc_jd_from_input(inp)
        try: cusps, ascmc = swe.houses_ex(jd, target_lat, target_lon, b'P')
        except: cusps, ascmc = swe.houses_ex(jd, target_lat, target_lon, b'W')
        houses = cusps[1:]
        planets_data = {}
        for p_name, p_id in SWISSEPH_OBJECTS.items():
            try:
                res, _ = swe.calc_ut(jd, p_id, swe.FLG_SWIEPH)
                pl_lon = res[0]
                house_num = 1
                for i in range(12):
                    c_start = houses[i]
                    c_end = houses[(i + 1) % 12]
                    if c_start < c_end:
                        if c_start <= pl_lon < c_end: house_num = i + 1; break
                    else:
                        if pl_lon >= c_start or pl_lon < c_end: house_num = i + 1; break
                planets_data[p_name] = {"absolute_degree": round(pl_lon, 4), "new_house": house_num}
            except: continue
        return {
            "city": city_name,
            "coordinates": {"lat": target_lat, "lon": target_lon},
            "angles": {"Ascendant": round(ascmc[0], 4), "MC": round(ascmc[1], 4)},
            "cusps": [round(h, 4) for h in houses],
            "planets_in_houses": planets_data
        }

    @measure_time
    def check_single_point(self, inp: BirthInput, target_lat: float, target_lon: float, target_name: str = "Target") -> Dict[str, Any]:
        acg_data = self.get_astrocartography_lines(inp)
        ls_data = self.get_local_space_lines(inp)
        
        single_city = [{"name": target_name, "lat": target_lat, "lon": target_lon, "country": "Custom Point"}]
        
        results = self.calculate_city_scores_combined(acg_data, ls_data, single_city, float(inp.lat), float(inp.lon))
        if results and len(results) > 0:
            return results[0]
        
        return {"name": target_name, "lat": target_lat, "lon": target_lon, "aspects": [], "is_crossing": False}

    @measure_time
    def check_local_space_point(self, inp: BirthInput, target_lat: float, target_lon: float, target_name: str = "Target") -> Dict[str, Any]:
        bearing_to_target = calculate_bearing(float(inp.lat), float(inp.lon), target_lat, target_lon)
        ls_data = self.get_local_space_lines(inp)
        LS_ORB_DEGREES = 3.0 
        aspects = []
        
        for planet, p_data in ls_data.items():
            planet_az = p_data['azimuth']
            
            diff_fwd = abs(bearing_to_target - planet_az)
            if diff_fwd > 180: diff_fwd = 360 - diff_fwd
            
            planet_az_rev = (planet_az + 180.0) % 360.0
            diff_rev = abs(bearing_to_target - planet_az_rev)
            if diff_rev > 180: diff_rev = 360 - diff_rev

            if diff_fwd <= LS_ORB_DEGREES:
                score = int(100 * (1 - diff_fwd/LS_ORB_DEGREES))
                aspects.append({"planet": planet, "type": "ls", "angle": "Local Space", "azimuth": round(planet_az, 2), "score": score})
            elif diff_rev <= LS_ORB_DEGREES:
                score = int(100 * (1 - diff_rev/LS_ORB_DEGREES))
                aspects.append({"planet": planet, "type": "ls", "angle": "Local Space (Оппозиция)", "azimuth": round(planet_az_rev, 2), "score": score})
                
        aspects.sort(key=lambda x: x['score'], reverse=True)
        return {
            "name": target_name, "center_lat": float(inp.lat), "center_lon": float(inp.lon),
            "lat": target_lat, "lon": target_lon, "bearing": round(bearing_to_target, 2),
            "aspects": aspects, "is_crossing": len(aspects) > 0
        }
    
    def get_local_space_chart(self, inp) -> Dict[str, Any]:
        """
        Рассчитывает круговую карту Local Space: 
        Азимуты (для радиальных линий), Высоту (над/под горизонтом) и аспекты.
        """
        # 1. Получаем Юлианский день (через Kerykeion для надежности)
        y, m, d = parse_ymd(inp.date)
        hh, mm = parse_hm(inp.time)
        subject = AstrologicalSubjectFactory.from_birth_data(
            name=inp.name, year=y, month=m, day=d, hour=hh, minute=mm,
            lng=float(inp.lon), lat=float(inp.lat), tz_str=tz_to_pytz(str(inp.tz))
        )
        jd = subject.julian_day
        
        # 2. Координаты наблюдателя (Долгота, Широта, Высота над морем = 0)
        geopos = (float(inp.lon), float(inp.lat), 0.0)
        
        ls_planets = []
        # Берем классические планеты + Хирон, Узлы и Лилит
        target_points = [
            "Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", 
            "Saturn", "Uranus", "Neptune", "Pluto", "Chiron", 
            "True_North_Lunar_Node", "Mean_Lilith"
        ]
        
        for p_name in target_points:
            swe_id = SWISSEPH_OBJECTS.get(p_name)
            if swe_id is None: continue
                
            # Получаем стандартные эклиптические координаты
            res_ecl, _ = swe.calc_ut(jd, swe_id, swe.FLG_SWIEPH)
            pos = (res_ecl[0], res_ecl[1], res_ecl[2]) # lon, lat, dist
            
            # Переводим эклиптику в горизонтальную систему координат
            # Флаг 0 означает входные данные из эклиптики
            azalt = swe.azalt(jd, 0, geopos, 0, 0, pos)
            
            # В SwissEph азимут по умолчанию считается от Юга (0°) к Западу (90°).
            # Переводим в классический компас: Север (0°), Восток (90°):
            raw_azimuth = azalt[0]
            compass_azimuth = (raw_azimuth + 180) % 360
            
            true_altitude = azalt[1]
            
            ls_planets.append({
                "name": p_name,
                "azimuth": round(compass_azimuth, 4),
                "altitude": round(true_altitude, 4),
                "is_above_horizon": true_altitude > 0
            })
            
        # 3. Считаем аспекты Local Space
        # Для LS используются строгие орбисы, так как энергия очень осязаема
        ls_aspect_rules = {
            0:   ("conjunction", 3.0),
            60:  ("sextile", 2.0),
            90:  ("square", 2.5),
            120: ("trine", 2.0),
            180: ("opposition", 3.0)
        }
        
        aspects = []
        for i in range(len(ls_planets)):
            for j in range(i + 1, len(ls_planets)):
                p1 = ls_planets[i]
                p2 = ls_planets[j]
                
                # Ищем кратчайшее расстояние по кругу
                diff = abs(p1["azimuth"] - p2["azimuth"])
                if diff > 180:
                    diff = 360 - diff
                    
                for angle, (asp_name, max_orb) in ls_aspect_rules.items():
                    orb = abs(diff - angle)
                    if orb <= max_orb:
                        aspects.append({
                            "p1": p1["name"],
                            "p2": p2["name"],
                            "type": asp_name,
                            "orb": round(orb, 4)
                        })
                        
        return {
            "meta": {
                "type": "local_space_chart",
                "lat": inp.lat,
                "lon": inp.lon
            },
            "planets": ls_planets,
            "aspects": aspects
        }