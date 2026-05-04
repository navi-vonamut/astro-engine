from fastapi import APIRouter, Depends
from app.deps import verify_internal_api_key
from app.engine.kerykeion_engine import KerykeionEngine
from app.engine.core.models import BirthInput
from app.schemas import LunarRequest  # 🔥 Импортируем чистую схему

router = APIRouter(tags=["lunar"])
_engine = KerykeionEngine()

@router.post("/lunar")
async def get_lunar(request: LunarRequest, api_key: str = Depends(verify_internal_api_key)):
    p = request.person
    
    # Конвертируем внешнюю схему во внутренний формат движка
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

    return _engine.lunar_return(
        natal_inp=natal_input,
        target_date=request.target_date,
        loc_lat=request.loc_lat,
        loc_lon=request.loc_lon,
        loc_tz=request.loc_tz
    )