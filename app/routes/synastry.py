from __future__ import annotations

from fastapi import APIRouter, Depends
from ..deps import verify_internal_api_key
from ..schemas import SynastryRequest
from ..engine.kerykeion_engine import KerykeionEngine, BirthInput

router = APIRouter(tags=["synastry"])

_engine = KerykeionEngine()

@router.post("/synastry")
async def synastry(request: SynastryRequest, api_key: str = Depends(verify_internal_api_key)):
    p1 = request.person1
    p2 = request.person2

    # Используем метод .synastry(), который возвращает и аспекты, и наложения (overlays)
    result = _engine.synastry(
        BirthInput("Owner", p1.date, p1.time, p1.tz, p1.lat, p1.lon),
        BirthInput("Partner", p2.date, p2.time, p2.tz, p2.lat, p2.lon),
    )
    return result