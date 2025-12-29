from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException

# Импорты из вашей структуры
from ..deps import verify_internal_api_key
from ..schemas import HoraryRequest 
from ..engine.kerykeion_engine import KerykeionEngine, BirthInput

router = APIRouter(tags=["horary"])

_engine = KerykeionEngine()

@router.post("/horary")
async def horary(request: HoraryRequest, api_key: str = Depends(verify_internal_api_key)):
    """
    Принимает запрос с UTC-временем (dt_utc), преобразует его
    в формат для Kerykeion (date, time, tz=+00:00) и строит карту.
    """
    try:
        # 1. Парсим строку времени (например "2025-12-29T01:32:05Z")
        if request.dt_utc.endswith("Z"):
            # fromisoformat в Python 3.10+ понимает 'Z', но для надежности убираем
            dt = datetime.fromisoformat(request.dt_utc[:-1]).replace(tzinfo=timezone.utc)
        else:
            dt = datetime.fromisoformat(request.dt_utc)
            # Если таймзона не указана, считаем что это UTC
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        
        # 2. Формируем входные данные для движка
        # Таймзону жестко ставим +00:00, так как мы привели время к UTC
        inp = BirthInput(
            name="Querent", 
            date=dt.strftime("%Y-%m-%d"),
            time=dt.strftime("%H:%M:%S"),
            tz="+00:00", 
            lat=request.lat,
            lon=request.lon,
        )

        # 3. Вызываем расчет
        # Метод .horary() сам посчитает дома и статусы
        result = _engine.horary(inp, request.question)
        return result

    except Exception as e:
        # Логируем ошибку, чтобы видеть в docker logs
        print(f"[Engine] Horary error: {e}")
        raise HTTPException(status_code=500, detail=f"Calculation error: {str(e)}")