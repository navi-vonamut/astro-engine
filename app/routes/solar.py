# routes/solar.py
from __future__ import annotations

from fastapi import APIRouter, Depends
from ..deps import verify_internal_api_key
from ..schemas import SolarReturnRequest
from ..engine.kerykeion_engine import KerykeionEngine, BirthInput

router = APIRouter(tags=["solar"])

_engine = KerykeionEngine()

@router.post("/solar")
async def calculate_solar(
    request: SolarReturnRequest, 
    api_key: str = Depends(verify_internal_api_key)
):
    # 1. Формируем объект рождения (Усинск)
    natal_req = request.user_data
    natal_inp = BirthInput(
        name="User",
        date=natal_req.date,
        time=natal_req.time,
        tz=natal_req.tz,
        lat=natal_req.lat,
        lon=natal_req.lon,
    )
    
    # 2. Определяем, где строим карту (Нижний или Усинск?)
    # Если передали return_lat, берем его. Если нет — берем координаты рождения.
    target_lat = request.return_lat if request.return_lat is not None else natal_req.lat
    target_lon = request.return_lon if request.return_lon is not None else natal_req.lon
    target_tz = request.return_tz if request.return_tz else natal_req.tz

    # 3. Вызываем движок с ДВУМЯ наборами координат
    return _engine.solar_return(
        natal_inp=natal_inp, 
        year=request.year,
        loc_lat=target_lat,
        loc_lon=target_lon,
        loc_tz=target_tz
    )