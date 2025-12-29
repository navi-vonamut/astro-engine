from __future__ import annotations

from typing import Dict, Any
from fastapi import APIRouter, Depends
from ..deps import verify_internal_api_key
from ..schemas import DailyPredictionRequest
from ..engine.kerykeion_engine import KerykeionEngine, BirthInput

router = APIRouter(prefix="/predict", tags=["predict"])

_engine = KerykeionEngine()

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