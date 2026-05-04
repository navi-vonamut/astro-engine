from fastapi import APIRouter, Depends
from app.deps import verify_internal_api_key
from app.engine.kerykeion_engine import KerykeionEngine
from app.schemas import ElectionalRequest

router = APIRouter(tags=["electional"])
_engine = KerykeionEngine()

@router.post("/electional")
async def get_electional_dates(request: ElectionalRequest, api_key: str = Depends(verify_internal_api_key)):
    return _engine.electional_search(
        start_date=request.start_date,
        end_date=request.end_date,
        lat=request.lat,
        lon=request.lon,
        tz=request.tz
    )