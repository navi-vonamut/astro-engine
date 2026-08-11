from fastapi import APIRouter, Depends
from app.deps import verify_internal_api_key
from app.engine.kerykeion_engine import KerykeionEngine
from app.engine.core.models import BirthInput
from app.schemas import RectificationRequest

router = APIRouter(tags=["rectification"])
_engine = KerykeionEngine()

@router.post("/rectify")
async def rectify_birth_time(request: RectificationRequest, api_key: str = Depends(verify_internal_api_key)):
    p = request.person
    
    # Собираем модель для движка. 
    # Время (p.time) здесь передается как есть, но в самом KerykeionEngine 
    # мы будем использовать фейковое 12:00 для расчета медленных планет.
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

    # Сериализуем объекты событий Pydantic в обычные словари для передачи в движок
    events_data = [ev.model_dump() for ev in request.events]

    return _engine.rectify(
        natal_inp=natal_input,
        events=events_data,
        mode=request.mode or "symbolic",
        max_orb=request.max_orb or 0.5,
        start_time=request.start_time or "00:00",
        end_time=request.end_time or "23:59",
    )
