from __future__ import annotations

from typing import Dict, Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.deps import verify_internal_api_key
from app.schemas import DailyPredictionRequest
from app.engine.kerykeion_engine import KerykeionEngine
from app.engine.core.models import BirthInput

router = APIRouter(prefix="/predict", tags=["predict"])

_engine = KerykeionEngine()

# --- СХЕМЫ ЗАПРОСОВ ---

class EphemerisEngineRequest(BaseModel):
    name: str = "User"
    date: str
    time: str
    tz: str
    lat: float
    lon: float
    start_date: str
    end_date: str
    step_days: int = 5

class FirdariaRequest(BaseModel):
    name: str = "User"
    date: str
    time: str
    tz: str
    lat: float
    lon: float
    target_date: str

# 🔥 ДОБАВЛЯЕМ СХЕМУ ДЛЯ МЕСЯЧНОГО ПРОГНОЗА
class MonthlyOverviewRequest(BaseModel):
    name: str = "User"
    date: str
    time: str
    tz: str
    lat: float
    lon: float
    year: int
    month: int


# 🔥 ДОБАВЛЯЕМ СХЕМУ ДЛЯ ГОДОВОЙ ДИАГРАММЫ ГАНТА
class AnnualGanttRequest(BaseModel):
    name: str = "User"
    date: str
    time: str
    tz: str
    lat: float
    lon: float
    year: int
    node_type: str = "true"

# --- РОУТЫ ---

@router.post("/daily")
async def predict_daily(request: DailyPredictionRequest, api_key: str = Depends(verify_internal_api_key)) -> Dict[str, Any]:
    natal = BirthInput(
        name="Natal",
        date=request.date,
        time=request.time,
        tz=request.tz,
        lat=request.lat,
        lon=request.lon,
    )

    result = _engine.transits(natal, request.target_date, extra_house_grids=request.extra_house_grids)
    
    return result

@router.post("/ephemeris")
async def get_ephemeris(request: EphemerisEngineRequest, api_key: str = Depends(verify_internal_api_key)) -> Dict[str, Any]:
    natal = BirthInput(
        name=request.name,
        date=request.date,
        time=request.time,
        tz=request.tz,
        lat=request.lat,
        lon=request.lon,
    )

    result = _engine.graphical_ephemeris(
        natal_inp=natal, 
        start_date=request.start_date, 
        end_date=request.end_date, 
        step_days=request.step_days
    )
    
    return result

@router.post("/firdaria")
async def get_firdaria(request: FirdariaRequest, api_key: str = Depends(verify_internal_api_key)) -> Dict[str, Any]:
    natal = BirthInput(
        name=request.name,
        date=request.date,
        time=request.time,
        tz=request.tz,
        lat=request.lat,
        lon=request.lon,
    )

    result = _engine.firdaria(natal_inp=natal, target_date=request.target_date)
    
    return result

# 🔥 ДОБАВЛЯЕМ РОУТ МЕСЯЧНОГО ПРОГНОЗА
@router.post("/monthly")
async def get_monthly_overview(request: MonthlyOverviewRequest, api_key: str = Depends(verify_internal_api_key)) -> Dict[str, Any]:
    natal = BirthInput(
        name=request.name,
        date=request.date,
        time=request.time,
        tz=request.tz,
        lat=request.lat,
        lon=request.lon,
    )

    # Вызываем метод monthly_overview из движка
    result = _engine.monthly_overview(natal_inp=natal, year=request.year, month=request.month)
    
    return result

# 🔥 РОУТ ГОДОВОЙ ДИАГРАММЫ ГАНТА
@router.post("/gantt")
@router.post("/gantt/")
@router.post("/transits/gantt")
async def get_annual_gantt(request: AnnualGanttRequest, api_key: str = Depends(verify_internal_api_key)) -> Dict[str, Any]:
    natal = BirthInput(
        name=request.name,
        date=request.date,
        time=request.time,
        tz=request.tz,
        lat=request.lat,
        lon=request.lon,
        node_type=request.node_type
    )

    result = _engine.annual_gantt_transits(natal_inp=natal, year=request.year)
    return result