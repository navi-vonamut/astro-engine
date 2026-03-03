from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List
from ..deps import verify_internal_api_key
from ..engine.kerykeion_engine import BirthInput
from ..engine.geo_engine import GeoAstroEngine

# Создаем роутер. Можно добавить префикс, чтобы урлы были красивыми, например /api/geo/...
router = APIRouter(
    prefix="/geo",
    tags=["AstroCartography & Relocation"]
)

# Инициализируем наш движок один раз для этого роутера
geo_engine = GeoAstroEngine()

class RelocationRequest(BaseModel):
    birth_data: BirthInput
    target_lat: float
    target_lon: float
    city_name: str

class BulkRelocationRequest(BaseModel):
    birth_data: BirthInput
    coordinates: List[dict] # Ожидаем [{"lat": x, "lon": y}, ...]

@router.post("/astrocartography")
async def calculate_astrocartography(inp: BirthInput, api_key: str = Depends(verify_internal_api_key)):
    """Возвращает массивы координат для рисования линий на карте мира"""
    try:
        lines = geo_engine.get_astrocartography_lines(inp)
        return {"status": "success", "data": lines}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/evaluate_city")
async def evaluate_city(req: RelocationRequest, api_key: str = Depends(verify_internal_api_key)):
    """Возвращает сырые астрономические данные релокации для Главного API"""
    try:
        raw_data = geo_engine.get_relocation_raw_data(
            req.birth_data, 
            req.target_lat, 
            req.target_lon, 
            req.city_name
        )
        return {"status": "success", "data": raw_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/evaluate_cities_bulk")
async def evaluate_cities_bulk(req: BulkRelocationRequest, api_key: str = Depends(verify_internal_api_key)):
    try:
        raw_data_list = geo_engine.get_bulk_relocation_raw(req.birth_data, req.coordinates)
        return {"status": "success", "data": raw_data_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))