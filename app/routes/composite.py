from __future__ import annotations

from fastapi import APIRouter, Depends

from app.deps import verify_internal_api_key
from app.schemas import SynastryRequest
from app.engine.kerykeion_engine import KerykeionEngine
from app.engine.core.models import BirthInput

router = APIRouter(tags=["composite"])

_engine = KerykeionEngine()

@router.post("/composite")
async def composite(request: SynastryRequest, api_key: str = Depends(verify_internal_api_key)):
    p1 = request.person1
    p2 = request.person2

    # Используем метод .composite(), который строит карту мидпойнтов
    result = _engine.composite(
        BirthInput("Person A", p1.date, p1.time, p1.tz, p1.lat, p1.lon),
        BirthInput("Person B", p2.date, p2.time, p2.tz, p2.lat, p2.lon),
    )
    return result