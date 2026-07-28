from fastapi import APIRouter, Depends
from app.deps import verify_internal_api_key
from app.engine.kerykeion_engine import KerykeionEngine
from app.engine.core.models import BirthInput
from app.schemas import DirectionsRequest

router = APIRouter(tags=["directions"])
_engine = KerykeionEngine()

@router.post("/directions")
async def get_directions(request: DirectionsRequest, api_key: str = Depends(verify_internal_api_key)):
    p = request.person
    
    natal_input = BirthInput(
        name=p.name or "User",
        date=p.date,
        time=p.time,
        tz=p.tz,
        lat=p.lat,
        lon=p.lon,
        house_system=p.house_system,
        node_type=p.node_type
    )

    return _engine.directions(
        natal_inp=natal_input,
        target_date=request.target_date,
        mode=request.mode or "symbolic",
        orb=request.orb or 1.0
    )
