from fastapi import APIRouter, Depends
from app.deps import verify_internal_api_key
from app.engine.kerykeion_engine import KerykeionEngine
from app.schemas import ContentHoroscopeRequest

router = APIRouter(tags=["content"])
_engine = KerykeionEngine()

@router.post("/content/horoscope")
async def get_content_horoscope(request: ContentHoroscopeRequest, api_key: str = Depends(verify_internal_api_key)):
    """Генерация астрологических событий (ингрессии и фазы) для контентных гороскопов"""
    return _engine.content_horoscope(
        sign=request.sign,
        start_date=request.start_date,
        end_date=request.end_date
    )