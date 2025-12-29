from __future__ import annotations

from fastapi import APIRouter, Depends
from ..deps import verify_internal_api_key
from ..schemas import NatalChartRequest
from ..engine.kerykeion_engine import KerykeionEngine, BirthInput

router = APIRouter(tags=["natal"])

_engine = KerykeionEngine()


@router.post("/natal")
async def natal(request: NatalChartRequest, api_key: str = Depends(verify_internal_api_key)):
    inp = BirthInput(
        name="Person",
        date=request.date,
        time=request.time,
        tz=request.tz,
        lat=request.lat,
        lon=request.lon,
    )
    return _engine.natal(inp)
