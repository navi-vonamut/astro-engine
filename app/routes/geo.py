from fastapi import APIRouter, HTTPException, Depends
from typing import List

from app.deps import verify_internal_api_key
from app.engine.core.models import BirthInput
from app.engine.geo_engine import GeoAstroEngine
from app.geo.cities import get_major_cities  # Нужен для Astrocartography-Full

from app.schemas import (
    NatalChartRequest, RelocationRequest, 
    BulkRelocationRequest, CheckPointRequest
)

router = APIRouter(
    prefix="/geo",
    tags=["AstroCartography & Relocation"]
)

# Инициализируем наш очищенный движок один раз для этого роутера
geo_engine = GeoAstroEngine()

# Хелпер для конвертации схемы API во внутреннюю модель движка
def to_birth_input(req: NatalChartRequest) -> BirthInput:
    return BirthInput(
        name=req.name or "User",
        date=req.date,
        time=req.time,
        tz=getattr(req, "tz", "UTC"), # Безопасное получение таймзоны
        lat=req.lat,
        lon=req.lon,
        house_system=req.house_system or "P",
        node_type=req.node_type or "true"
    )

# =================================================================
# 1. ПОЛНАЯ КАРТА МИРА (ACG + LS + Города) -> Перенесено из internal
# =================================================================
@router.post("/astrocartography-full")
async def calculate_full_map(req: NatalChartRequest, api_key: str = Depends(verify_internal_api_key)):
    try:
        inp = to_birth_input(req)
        map_data = geo_engine.get_astrocartography_lines(inp)
        ls_data = geo_engine.get_local_space_lines(inp)
        
        cities = get_major_cities()
        scored_cities = geo_engine.calculate_city_scores_combined(
            map_data, ls_data, cities, float(inp.lat), float(inp.lon)
        )

        return {
            "status": "success",
            "lines": map_data,
            "ls_data": ls_data,
            "cities": scored_cities
        }
    except Exception as e:
        print(f"❌ CRITICAL ENGINE ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =================================================================
# 2. ТОЛЬКО ЛИНИИ ACG
# =================================================================
@router.post("/astrocartography")
async def calculate_astrocartography(req: NatalChartRequest, api_key: str = Depends(verify_internal_api_key)):
    try:
        inp = to_birth_input(req)
        lines = geo_engine.get_astrocartography_lines(inp)
        return {"status": "success", "data": lines}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =================================================================
# 3. ТОЛЬКО ЛИНИИ LOCAL SPACE -> Перенесено из internal
# =================================================================
@router.post("/local-space")
async def calculate_local_space(req: NatalChartRequest, api_key: str = Depends(verify_internal_api_key)):
    try:
        inp = to_birth_input(req)
        ls_data = geo_engine.get_local_space_lines(inp)
        return {"status": "success", "ls_data": ls_data}
    except Exception as e:
        print(f"❌ CRITICAL ENGINE ERROR (Local Space): {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =================================================================
# 4. СЫРЫЕ ДАННЫЕ РЕЛОКАЦИИ ПО ГОРОДАМ
# =================================================================
@router.post("/evaluate_city")
async def evaluate_city(req: RelocationRequest, api_key: str = Depends(verify_internal_api_key)):
    try:
        inp = to_birth_input(req) # Используем ту же схему (работает благодаря наследованию)
        raw_data = geo_engine.get_relocation_raw_data(inp, req.target_lat, req.target_lon, req.city_name)
        return {"status": "success", "data": raw_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/evaluate_cities_bulk")
async def evaluate_cities_bulk(req: BulkRelocationRequest, api_key: str = Depends(verify_internal_api_key)):
    try:
        inp = to_birth_input(req)
        raw_data_list = geo_engine.get_bulk_relocation_raw(inp, req.coordinates)
        return {"status": "success", "data": raw_data_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =================================================================
# 5. ТОЧЕЧНАЯ ПРОВЕРКА (Клик по карте)
# =================================================================
@router.post("/check_point")
async def check_point(req: CheckPointRequest, api_key: str = Depends(verify_internal_api_key)):
    try:
        inp = to_birth_input(req)
        result = geo_engine.check_single_point(inp, req.target_lat, req.target_lon, req.target_name)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/check-local-point") # 🔥 Сменил URL с '_' на '-', чтобы совпадало с page.tsx
async def check_local_space_point_route(req: CheckPointRequest, api_key: str = Depends(verify_internal_api_key)):
    try:
        inp = to_birth_input(req)
        result = geo_engine.check_local_space_point(inp, req.target_lat, req.target_lon, req.target_name)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

# =================================================================
# 6. LOCAL SPACE CHART (АЗИМУТЫ, ВЫСОТА И ЛОКАЛЬНЫЕ АСПЕКТЫ)
# =================================================================
@router.post("/local-space-chart")
async def local_space_chart_route(req: NatalChartRequest, api_key: str = Depends(verify_internal_api_key)):
    """Возвращает круговую карту Local Space: азимуты, высоту и локальные аспекты"""
    try:
        inp = to_birth_input(req)
        # Вызываем наш новый метод
        data = geo_engine.get_local_space_chart(inp)
        return {"status": "success", "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))