from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

# Импортируем нашу логику и защиту
from app.engine.geo_engine import GeoAstroEngine
from app.geo.cities import get_major_cities
from app.deps import verify_internal_api_key 

# Адаптер для BirthInput (fallback)
try:
    from app.engine.kerykeion_engine import BirthInput
except ImportError:
    BirthInput = None

router = APIRouter(prefix="/internal", tags=["Internal Calculation Engine"])

class EngineRequest(BaseModel):
    name: str
    date: str
    time: str
    lat: float
    lon: float
    tz: str

class SimpleBirthInput:
    def __init__(self, name, date, time, lat, lon, tz):
        self.name = name; self.date = date; self.time = time
        self.lat = lat; self.lon = lon; self.tz = tz

# =================================================================
# 1. ПОЛНАЯ КАРТА МИРА (ACG + LS + Города)
# =================================================================
@router.post("/astrocartography-full", dependencies=[Depends(verify_internal_api_key)])
async def calculate_full_map(req: EngineRequest):
    try:
        # 1. Формируем Input
        if BirthInput:
            inp = BirthInput(name=req.name, date=req.date, time=req.time, lat=req.lat, lon=req.lon, tz=req.tz)
        else:
            inp = SimpleBirthInput(name=req.name, date=req.date, time=req.time, lat=req.lat, lon=req.lon, tz=req.tz)

        # 2. Инициализируем движок
        engine = GeoAstroEngine()
        
        # 3. Считаем линии
        # ACG (Планеты на углах)
        map_data = engine.get_astrocartography_lines(inp)
        # LS (Азимуты от места рождения)
        ls_data = engine.get_local_space_lines(inp)
        
        # 4. Получаем города и считаем баллы (КОМБИНИРОВАННЫЙ МЕТОД)
        cities = get_major_cities()
        
        # Используем новый метод, который находит пересечения ACG + LS
        scored_cities = engine.calculate_city_scores_combined(
            map_data, 
            ls_data, 
            cities,
            float(req.lat), 
            float(req.lon)
        )

        return {
            "status": "success",
            "lines": map_data,      # Линии ACG
            "ls_data": ls_data,     # Линии Local Space (для отрисовки пунктиром)
            "cities": scored_cities # Города (с пометкой is_crossing)
        }

    except Exception as e:
        print(f"❌ CRITICAL ENGINE ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =================================================================
# 2. ТОЛЬКО LOCAL SPACE (Для интерактивной карты)
# =================================================================
@router.post("/local-space", dependencies=[Depends(verify_internal_api_key)])
async def calculate_local_space(req: EngineRequest):
    try:
        # Формируем Input
        if BirthInput:
            inp = BirthInput(name=req.name, date=req.date, time=req.time, lat=req.lat, lon=req.lon, tz=req.tz)
        else:
            inp = SimpleBirthInput(name=req.name, date=req.date, time=req.time, lat=req.lat, lon=req.lon, tz=req.tz)

        engine = GeoAstroEngine()
        
        # Считаем только азимуты (это быстро)
        ls_data = engine.get_local_space_lines(inp)
        
        return {
            "status": "success",
            "ls_data": ls_data
        }

    except Exception as e:
        print(f"❌ CRITICAL ENGINE ERROR (Local Space): {e}")
        raise HTTPException(status_code=500, detail=str(e))