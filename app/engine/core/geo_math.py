import math
import numpy as np
from typing import List

def to_dms(deg: float) -> str:
    """Перевод десятичных градусов в градусы, минуты и секунды."""
    d = int(deg)
    m = int((deg - d) * 60)
    s = int(((deg - d) * 60 - m) * 60)
    return f"{d}°{m:02d}'{s:02d}\""

def normalize_lon(lon: float) -> float:
    """Нормализация долготы в диапазон от -180 до +180."""
    lon = lon % 360
    if lon > 180:
        lon -= 360
    return round(lon, 5)

def destination_point(lat: float, lon: float, bearing: float, distance_km: float) -> List[float]:
    """Вычисляет координаты точки назначения по начальной точке, азимуту и дистанции."""
    R = 6371.0 
    lat1 = math.radians(lat)
    lon1 = math.radians(lon)
    brng = math.radians(bearing)
    lat2 = math.asin(math.sin(lat1)*math.cos(distance_km/R) +
                     math.cos(lat1)*math.sin(distance_km/R)*math.cos(brng))
    lon2 = lon1 + math.atan2(math.sin(brng)*math.sin(distance_km/R)*math.cos(lat1),
                             math.cos(distance_km/R)-math.sin(lat1)*math.sin(lat2))
    return [math.degrees(lat2), normalize_lon(math.degrees(lon2))]

def generate_geodesic_path(start_lat: float, start_lon: float, azimuth: float, max_dist_km: int = 20000) -> List[List[List[float]]]:
    """Генерирует векторным способом массив точек для отрисовки геодезической линии (луча Local Space)."""
    R = 6371.0
    steps = np.array([1, 3, 5, 10, 25, 50, 100] + list(range(200, max_dist_km, 200)), dtype=np.float64)
    
    lat1 = math.radians(start_lat)
    lon1 = math.radians(start_lon)
    brng = math.radians(azimuth)
    
    d_over_r = steps / R
    sin_d = np.sin(d_over_r)
    cos_d = np.cos(d_over_r)
    sin_lat1 = math.sin(lat1)
    cos_lat1 = math.cos(lat1)
    cos_brng = math.cos(brng)
    sin_brng = math.sin(brng)
    
    lat2_arr = np.arcsin(np.clip(sin_lat1 * cos_d + cos_lat1 * sin_d * cos_brng, -1.0, 1.0))
    lon2_arr = lon1 + np.arctan2(sin_brng * sin_d * cos_lat1, cos_d - sin_lat1 * np.sin(lat2_arr))
    
    lats_deg = np.degrees(lat2_arr)
    lons_deg = (np.degrees(lon2_arr) % 360 + 540) % 360 - 180
    
    points = []
    segment = [[float(start_lat), float(start_lon)]]
    prev_lon = float(start_lon)
    
    for i in range(len(steps)):
        lat_val = round(float(lats_deg[i]), 5)
        lon_val = round(float(lons_deg[i]), 5)
        if abs(lon_val - prev_lon) > 180:
            points.append(segment)
            segment = []
        segment.append([lat_val, lon_val])
        prev_lon = lon_val
        
    if segment:
        points.append(segment)
    return points

def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Вычисляет азимут (направление) от первой точки ко второй."""
    dLon = math.radians(lon2 - lon1)
    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)
    y = math.sin(dLon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dLon)
    brng = math.atan2(y, x)
    return (math.degrees(brng) + 360) % 360

def interpolate_dateline(prev_lat: float, prev_lon: float, curr_lat: float, curr_lon: float):
    """Интерполяция при пересечении линии перемены дат (для красивой отрисовки линий на карте)."""
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