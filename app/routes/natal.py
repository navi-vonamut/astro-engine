from __future__ import annotations

from fastapi import APIRouter, Depends
from ..deps import verify_internal_api_key
from ..schemas import NatalChartRequest
from ..engine.kerykeion_engine import KerykeionEngine, BirthInput

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
    """Тяжелый расчет для Сайта (JSON + SVG картинка)"""
    
    # Желательно передавать имя, так как Kerykeion печатает его прямо на самой SVG картинке.
    # Если в NatalChartRequest еще нет поля name, можно пока оставить "User" или добавить его в схему.
    client_name = getattr(request, "name", "User") 

    inp = BirthInput(
        name=client_name,
        date=request.date,
        time=request.time,
        tz=request.tz,
        lat=request.lat,
        lon=request.lon,
    )
    
    # 1. Получаем все расчеты планет, домов, аспектов
    chart_data = _engine.natal(inp)
    
    # 2. Генерируем SVG код (метод, который мы добавили в KerykeionEngine)
    svg_string = _engine.get_natal_svg(inp)
    
    # 3. Вшиваем картинку в ответ
    chart_data["svg"] = svg_string
    
    return chart_data