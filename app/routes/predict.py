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

    # Используем новый метод .transits(), который вернет { transit_planets (с домами!), aspects }
    result = _engine.transits(natal, request.target_date)
    
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

    # Вызываем метод, который мы только что написали
    result = _engine.graphical_ephemeris(
        natal_inp=natal, 
        start_date=request.start_date, 
        end_date=request.end_date, 
        step_days=request.step_days
    )
    
    return result