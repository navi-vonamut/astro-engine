from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class NatalChartRequest(BaseModel):
    date: str = Field(..., description="YYYY-MM-DD or YYYY/MM/DD")
    time: str = Field(..., description="HH:MM:SS")
    tz: str = Field(..., description="Timezone like +03:00 or Europe/Warsaw")
    lat: float
    lon: float
    name: Optional[str] = "User"
    house_system: Optional[str] = "P"
    node_type: Optional[str] = "true"


class DailyPredictionRequest(BaseModel):
    date: str
    time: str
    tz: str
    lat: float
    lon: float
    target_date: str = Field(..., description="YYYY-MM-DD or YYYY/MM/DD")


class SynastryRequest(BaseModel):
    person1: NatalChartRequest
    person2: NatalChartRequest


class Transit(BaseModel):
    transit_planet: str
    aspect: str
    natal_planet: str
    orb: float
    is_applying: bool = False


class TransitsResponse(BaseModel):
    target_date: str
    transits: List[Transit]

class HoraryRequest(BaseModel):
    lat: float
    lon: float
    question: str
    dt_utc: str

class SolarReturnRequest(BaseModel):
    user_data: NatalChartRequest = Field(..., description="Данные рождения (Усинск)")
    year: int
    return_lat: float | None = Field(None, description="Широта места пребывания (Н.Новгород)")
    return_lon: float | None = Field(None, description="Долгота места пребывания (Н.Новгород)")
    return_tz: str | None = Field(None, description="Часовой пояс места пребывания")

class RelocationRequest(NatalChartRequest):
    target_lat: float
    target_lon: float
    city_name: str

class BulkRelocationRequest(NatalChartRequest):
    coordinates: List[dict] # Ожидаем [{"lat": x, "lon": y}, ...]

class CheckPointRequest(NatalChartRequest):
    target_lat: float
    target_lon: float
    target_name: str