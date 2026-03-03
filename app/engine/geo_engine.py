import swisseph as swe
import math
import pytz
import numpy as np
import time
from datetime import datetime
from typing import Dict, Any, List

try:
    from .kerykeion_engine import BirthInput
except ImportError:
    pass

def measure_time(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        return result
    return wrapper

class GeoAstroEngine:
    def __init__(self):
        self.PLANETS = {
            'Sun': swe.SUN, 'Moon': swe.MOON, 'Mercury': swe.MERCURY,
            'Venus': swe.VENUS, 'Mars': swe.MARS, 'Jupiter': swe.JUPITER,
            'Saturn': swe.SATURN, 'Uranus': swe.URANUS, 'Neptune': swe.NEPTUNE,
            'Pluto': swe.PLUTO,
            'Chiron': swe.CHIRON,
            'Lilith': swe.MEAN_APOG,
            'Node': swe.TRUE_NODE
        }

    # === НОВЫЙ ХЕЛПЕР: ПЕРЕВОД В ГРАДУСЫ-МИНУТЫ-СЕКУНДЫ ===
    def to_dms(self, deg):
        d = int(deg)
        m = int((deg - d) * 60)
        s = int(((deg - d) * 60 - m) * 60)
        return f"{d}°{m:02d}'{s:02d}\""

    def _normalize_lon(self, lon: float) -> float:
        lon = lon % 360
        if lon > 180:
            lon -= 360
        return round(lon, 5) # Увеличил точность до 5

    def _get_utc_jd(self, inp: BirthInput) -> float:
        """Расчет JD с учетом таймзоны."""
        try:
            date_str = inp.date.replace('/', '-')
            if '-' in date_str:
                parts = date_str.split('-')
                y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
            else:
                dt_obj = datetime.strptime(date_str, "%Y-%m-%d")
                y, m, d = dt_obj.year, dt_obj.month, dt_obj.day
        except:
             dt_obj = datetime.strptime(inp.date, "%Y-%m-%d")
             y, m, d = dt_obj.year, dt_obj.month, dt_obj.day

        try:
            t_parts = inp.time.split(':')
            h = int(t_parts[0])
            mn = int(t_parts[1])
            s = float(t_parts[2]) if len(t_parts) > 2 else 0.0
        except:
            h, mn, s = 12, 0, 0

        offset_hours = 0.0
        tz_str = inp.tz
        try:
            if tz_str:
                tz = pytz.timezone(tz_str)
                dt_local = datetime(y, m, d, h, mn, int(s))
                dt_aware = tz.localize(dt_local)
                offset_duration = dt_aware.utcoffset()
                offset_hours = offset_duration.total_seconds() / 3600.0
        except Exception as e:
            print(f"⚠️ Timezone Error ({tz_str}): {e}. Using UTC.")
            offset_hours = 0.0

        hour_decimal_local = h + (mn / 60.0) + (s / 3600.0)
        hour_decimal_utc = hour_decimal_local - offset_hours
        
        jd = swe.julday(y, m, d, hour_decimal_utc)
        return jd

    def _destination_point(self, lat, lon, bearing, distance_km):
        R = 6371.0 
        lat1 = math.radians(lat)
        lon1 = math.radians(lon)
        brng = math.radians(bearing)
        lat2 = math.asin(math.sin(lat1)*math.cos(distance_km/R) +
                         math.cos(lat1)*math.sin(distance_km/R)*math.cos(brng))
        lon2 = lon1 + math.atan2(math.sin(brng)*math.sin(distance_km/R)*math.cos(lat1),
                                 math.cos(distance_km/R)-math.sin(lat1)*math.sin(lat2))
        return [math.degrees(lat2), self._normalize_lon(math.degrees(lon2))]

    def _generate_geodesic_path(self, start_lat, start_lon, azimuth, max_dist_km=20000):
        points = []
        segment = []
        segment.append([float(start_lat), float(start_lon)]) 
        prev_lon = float(start_lon)
        for dist in range(200, max_dist_km, 200):
            pt = self._destination_point(float(start_lat), float(start_lon), azimuth, dist)
            if abs(pt[1] - prev_lon) > 180:
                points.append(segment)
                segment = []
            segment.append(pt)
            prev_lon = pt[1]
        points.append(segment)
        return points

    def _calculate_bearing(self, lat1, lon1, lat2, lon2):
        dLon = math.radians(lon2 - lon1)
        lat1 = math.radians(lat1)
        lat2 = math.radians(lat2)
        y = math.sin(dLon) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dLon)
        brng = math.atan2(y, x)
        return (math.degrees(brng) + 360) % 360

    def _interpolate_dateline(self, prev_lat, prev_lon, curr_lat, curr_lon):
        if prev_lon > 0 and curr_lon < 0:
            edge_lon = 180.0; next_start_lon = -180.0
        elif prev_lon < 0 and curr_lon > 0:
            edge_lon = -180.0; next_start_lon = 180.0
        else: return None, None
        dist_to_edge = abs(edge_lon - prev_lon)
        dist_total = abs(360 - abs(prev_lon - curr_lon))
        fraction = 0.5 if dist_total < 0.0001 else dist_to_edge / dist_total
        mid_lat = prev_lat + (curr_lat - prev_lat) * fraction
        return [mid_lat, edge_lon], [mid_lat, next_start_lon]

    # ==========================================
    # 1. АСТРОКАРТОГРАФИЯ (ACG)
    # ==========================================
    @measure_time
    def get_astrocartography_lines(self, inp: BirthInput) -> Dict[str, Any]:
        # (Код ACG оставляем без изменений для краткости - он работает)
        result = {}
        jd = self._get_utc_jd(inp)
        gst_deg = swe.sidtime(jd) * 15.0
        MAX_MERCATOR_LAT = 85.0
        base_lats = np.arange(-MAX_MERCATOR_LAT, MAX_MERCATOR_LAT + 1, 1.0).tolist()
        for p_name, p_id in self.PLANETS.items():
            try:
                res, _ = swe.calc_ut(jd, p_id, swe.FLG_SWIEPH | swe.FLG_EQUATORIAL)
            except Exception: continue
            ra, decl = res[0], res[1]
            lines = {"MC": [], "IC": [], "ASC": [], "DSC": [], "Zenith": []}
            lon_mc = self._normalize_lon(ra - gst_deg); lon_ic = self._normalize_lon(ra - gst_deg + 180.0)
            mc_pts, ic_pts = [], []
            for lat in range(int(-MAX_MERCATOR_LAT), int(MAX_MERCATOR_LAT) + 1, 5): 
                mc_pts.append([float(lat), round(lon_mc, 3)]); ic_pts.append([float(lat), round(lon_ic, 3)])
            lines["MC"] = [mc_pts]; lines["IC"] = [ic_pts]; lines["Zenith"] = [round(decl, 3), round(lon_mc, 3)]
            asc_segments, dsc_segments = [], []; curr_asc, curr_dsc = [], []; prev_asc, prev_dsc = None, None
            limit_real = 90.0 - abs(decl); limit_map = min(limit_real, MAX_MERCATOR_LAT)
            lats = [lat for lat in base_lats if abs(lat) < (limit_map - 2.0)]
            if limit_real < MAX_MERCATOR_LAT:
                steps = [2.0, 1.0, 0.5, 0.2, 0.1, 0.05, 0.01]
                for s in steps:
                    if (limit_map - s) > lats[-1]: lats.extend([limit_map - s, -limit_map + s])
                lats.extend([limit_map, -limit_map])
            else: lats.extend([MAX_MERCATOR_LAT, -MAX_MERCATOR_LAT])
            lats = sorted(list(set(lats))); decl_rad = math.radians(decl); tan_decl = math.tan(decl_rad)
            for lat in lats:
                try: tan_lat = math.tan(math.radians(lat)); cos_h = -tan_lat * tan_decl
                except: continue
                if cos_h > 1.0: cos_h = 1.0
                elif cos_h < -1.0: cos_h = -1.0
                h_deg = math.degrees(math.acos(cos_h))
                lon_asc = self._normalize_lon((ra - h_deg) - gst_deg)
                if prev_asc is not None:
                    p_lat, p_lon = prev_asc; diff = lon_asc - p_lon
                    if abs(diff) > 180:
                        pt_end, pt_start = self._interpolate_dateline(p_lat, p_lon, lat, lon_asc)
                        if pt_end: curr_asc.append(pt_end); asc_segments.append(curr_asc); curr_asc = [pt_start]
                    elif abs(lat) >= (MAX_MERCATOR_LAT - 0.1) and abs(diff) > 20: asc_segments.append(curr_asc); curr_asc = []
                curr_asc.append([lat, round(lon_asc, 3)]); prev_asc = (lat, lon_asc)
                lon_dsc = self._normalize_lon((ra + h_deg) - gst_deg)
                if prev_dsc is not None:
                    p_lat, p_lon = prev_dsc; diff = lon_dsc - p_lon
                    if abs(diff) > 180:
                        pt_end, pt_start = self._interpolate_dateline(p_lat, p_lon, lat, lon_dsc)
                        if pt_end: curr_dsc.append(pt_end); dsc_segments.append(curr_dsc); curr_dsc = [pt_start]
                    elif abs(lat) >= (MAX_MERCATOR_LAT - 0.1) and abs(diff) > 20: dsc_segments.append(curr_dsc); curr_dsc = []
                curr_dsc.append([lat, round(lon_dsc, 3)]); prev_dsc = (lat, lon_dsc)
            if curr_asc: asc_segments.append(curr_asc)
            if curr_dsc: dsc_segments.append(curr_dsc)
            lines["ASC"] = asc_segments; lines["DSC"] = dsc_segments
            result[p_name] = lines
        return result

    # ==========================================
    # 2. LOCAL SPACE (ВЫСОКАЯ ТОЧНОСТЬ + ЛОГИ)
    # ==========================================
    @measure_time
    def get_local_space_lines(self, inp: BirthInput) -> Dict[str, Any]:
        jd = self._get_utc_jd(inp)
        swe.set_topo(float(inp.lon), float(inp.lat), 0.0)
        observer_coords = (float(inp.lon), float(inp.lat), 0.0)
        
        lines = {}

        # --- A) УГЛЫ (ASC, MC) ---
        try:
            cusps, ascmc = swe.houses(jd, float(inp.lat), float(inp.lon), b'P')
            asc_deg = ascmc[0]
            mc_deg = ascmc[1]
            ecl_res = swe.calc_ut(jd, swe.ECL_NUT, 0)
            true_obliquity = ecl_res[0][1]

            angles_map = {'Ascendant': asc_deg, 'MC': mc_deg}
            for name, lon_deg in angles_map.items():
                t_res = swe.cotrans((lon_deg, 0.0, 1.0), -true_obliquity)
                ra, dec = t_res[0], t_res[1]
                point_coords = (ra, dec, 1.0)
                
                # Без рефракции
                res_az = swe.azalt(jd, swe.EQU2HOR, observer_coords, 0.0, 0.0, point_coords)
                az_north = (res_az[0] + 180.0) % 360.0

                print(f"📐 {name}: {az_north:.4f}° -> {self.to_dms(az_north)}")

                forward = self._generate_geodesic_path(inp.lat, inp.lon, az_north, 20000)
                reverse = self._generate_geodesic_path(inp.lat, inp.lon, (az_north + 180) % 360, 20000)

                lines[name] = {
                    "azimuth": round(az_north, 4), # 4 знака точности
                    "forward_paths": forward,
                    "reverse_paths": reverse 
                }
        except Exception as e:
            print(f"❌ Error Angles: {e}")

        # --- B) ПЛАНЕТЫ ---
        for p_name, p_id in self.PLANETS.items():
            try:
                flags = swe.FLG_SWIEPH | swe.FLG_TOPOCTR | swe.FLG_EQUATORIAL
                res_pos = swe.calc_ut(jd, p_id, flags)
                planet_coords = tuple(res_pos[0])[:3]
                
                res_az = swe.azalt(jd, swe.EQU2HOR, observer_coords, 0.0, 0.0, planet_coords)
                az_north = (res_az[0] + 180.0) % 360.0
                
                # Логируем, чтобы вы могли сверить с Astro.com
                # print(f"🪐 {p_name}: {az_north:.4f}° -> {self.to_dms(az_north)}")

            except Exception as e:
                continue

            forward = self._generate_geodesic_path(inp.lat, inp.lon, az_north, 20000)
            reverse = self._generate_geodesic_path(inp.lat, inp.lon, (az_north + 180) % 360, 20000)

            lines[p_name] = {
                "azimuth": round(az_north, 4), # 4 знака точности
                "forward_paths": forward,
                "reverse_paths": reverse
            }

        return lines

    # ==========================================
    # 3. COMBINED SCORING (Оставляем как есть)
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
            bearing_to_city = self._calculate_bearing(birth_lat, birth_lon, city['lat'], city['lon'])
            ls_aspects = []
            if ls_data:
                for planet, p_data in ls_data.items():
                    planet_az = p_data['azimuth']
                    diff = abs(bearing_to_city - planet_az)
                    if diff > 180: diff = 360 - diff
                    if diff <= LS_ORB_DEGREES:
                        score = 50 * (1 - diff/LS_ORB_DEGREES)
                        ls_aspects.append({"planet": planet, "angle": "Local Space", "distance_km": 0, "score": int(score), "type": "ls"})
            
            has_acg = len(current_aspects) > 0; has_ls = len(ls_aspects) > 0; is_crossing = has_acg and has_ls
            all_aspects = current_aspects + ls_aspects
            all_aspects.sort(key=lambda x: x['score'], reverse=True)
            if all_aspects:
                c_copy = city.copy(); c_copy['aspects'] = all_aspects; c_copy['is_crossing'] = is_crossing
                final_cities.append(c_copy)
                
        return final_cities

    def get_relocation_raw_data(self, inp: BirthInput, target_lat: float, target_lon: float, city_name: str) -> Dict[str, Any]:
        jd = self._get_utc_jd(inp)
        try: cusps, ascmc = swe.houses_ex(jd, target_lat, target_lon, b'P')
        except: cusps, ascmc = swe.houses_ex(jd, target_lat, target_lon, b'W')
        houses = cusps[1:]
        planets_data = {}
        for p_name, p_id in self.PLANETS.items():
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