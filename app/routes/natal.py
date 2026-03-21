from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from app.deps import verify_internal_api_key
from app.schemas import NatalChartRequest
from app.engine.kerykeion_engine import KerykeionEngine
from app.engine.core.models import BirthInput

router = APIRouter(tags=["natal"])

_engine = KerykeionEngine()

@router.post("/natal")
async def natal(request: NatalChartRequest, api_key: str = Depends(verify_internal_api_key)):
    """Обычный расчет для Телеграм-бота (только JSON)"""
    inp = BirthInput(
        name="Person",
        date=request.date,
        time=request.time,
        tz=request.tz,
        lat=request.lat,
        lon=request.lon,
    )
    return _engine.natal(inp)


@router.post("/natal_web")
async def natal_web(request: NatalChartRequest, api_key: str = Depends(verify_internal_api_key)):
    """Основной расчет для Сайта (Только JSON данные)"""
    
    client_name = getattr(request, "name", "User") 
    h_sys = getattr(request, "house_system", "P")
    n_type = getattr(request, "node_type", "true") 

    inp = BirthInput(
        name=client_name,
        date=request.date,
        time=request.time,
        tz=request.tz,
        lat=request.lat,
        lon=request.lon,
        house_system=h_sys,
        node_type=n_type
    )
    
    # Теперь мы возвращаем ТОЛЬКО данные, без тяжелого SVG
    chart_data = _engine.natal(inp)
    return chart_data


@router.post("/natal_svg")
async def natal_svg(request: NatalChartRequest, api_key: str = Depends(verify_internal_api_key)):
    """Отдельная ручка для генерации SVG картинки (Вызывается по кнопке)"""
    
    client_name = getattr(request, "name", "User") 
    h_sys = getattr(request, "house_system", "P")

    inp = BirthInput(
        name=client_name,
        date=request.date,
        time=request.time,
        tz=request.tz,
        lat=request.lat,
        lon=request.lon,
        house_system=h_sys
    )
    
    svg_string = _engine.get_natal_svg(inp)
    
    # Возвращаем SVG текстом (фронтенд сможет вставить его через dangerouslySetInnerHTML)
    return {"status": "success", "svg": svg_string}