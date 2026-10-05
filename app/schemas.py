from __future__ import annotations

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class NatalChartRequest(BaseModel):
    date: str = Field(..., description="YYYY-MM-DD or YYYY/MM/DD")
    time: Optional[str] = Field("12:00", description="HH:MM:SS (defaults to 12:00 if empty)")
    tz: Optional[str] = Field("+00:00", description="Timezone like +03:00 or Europe/Warsaw")
    lat: float
    lon: float
    name: Optional[str] = "User"
    house_system: Optional[str] = "P"
    node_type: Optional[str] = "true"
    coord_system: Optional[str] = ""
    custom_orbs: Optional[Dict[str, float]] = None


class DailyPredictionRequest(BaseModel):
    date: str
    time: str
    tz: str
    lat: float
    lon: float
    target_date: str = Field(..., description="YYYY-MM-DD or YYYY/MM/DD")
    extra_house_grids: Optional[Dict[str, List[Dict[str, Any]]]] = None


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

class LunarRequest(BaseModel):
    person: NatalChartRequest = Field(..., description="Данные рождения")
    target_date: str = Field(..., description="Целевая дата в формате YYYY-MM-DD")
    loc_lat: float = Field(..., description="Широта места пребывания")
    loc_lon: float = Field(..., description="Долгота места пребывания")
    loc_tz: str = Field(..., description="Часовой пояс места пребывания")

class ProgressionRequest(BaseModel):
    person: NatalChartRequest = Field(..., description="Данные рождения")
    target_date: str = Field(..., description="Целевая дата прогноза (на какой момент смотрим) в формате YYYY-MM-DD")

class ElectionalRequest(BaseModel):
    start_date: str = Field(..., description="Начало периода (YYYY-MM-DD)")
    end_date: str = Field(..., description="Конец периода (YYYY-MM-DD)")
    lat: float
    lon: float
    tz: str
    category: Optional[str] = Field("business", description="Категория подбора даты")

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

class ContentHoroscopeRequest(BaseModel):
    sign: str = Field(..., description="Короткое имя знака (Ari, Tau, Gem, Can, Leo, Vir, Lib, Sco, Sag, Cap, Aqu, Pis)")
    start_date: str = Field(..., description="Начало периода прогноза (YYYY-MM-DD)")
    end_date: str = Field(..., description="Конец периода прогноза (YYYY-MM-DD)")

class DirectionsRequest(BaseModel):
    person: NatalChartRequest = Field(..., description="Данные рождения")
    target_date: str = Field(..., description="Целевая дата прогноза в формате YYYY-MM-DD")
    mode: Optional[str] = Field("symbolic", description="Режим: 'symbolic' (1° = 1 год) или 'solar_arc'")
    orb: Optional[float] = Field(1.0, description="Максимальный орбис в градусах (стандарт 1.0°)")

class LifeEvent(BaseModel):
    target_date: str = Field(..., description="Target date of the event in YYYY-MM-DD format (fallback to English)")
    event_type: str = Field(..., description="Type of the event, e.g., 'marriage', 'childbirth' (fallback to English)")
    weight: float = Field(1.0, description="Weight or importance multiplier of the event, default is 1.0 (fallback to English)")

class RectificationRequest(BaseModel):
    person: NatalChartRequest = Field(..., description="Base natal data. Time is ignored as it will be calculated (fallback to English)")
    events: List[LifeEvent] = Field(..., description="List of significant life events for matching (fallback to English)")
    mode: Optional[str] = Field("symbolic", description="Direction mode, 'symbolic' by default (fallback to English)")
    max_orb: Optional[float] = Field(0.5, description="Maximum allowed orb for aspect matching")
    start_time: Optional[str] = Field("00:00", description="Start of search window HH:MM")
    end_time: Optional[str] = Field("23:59", description="End of search window HH:MM")
    ai_signatures: Optional[dict] = Field(None, description="AI-generated event signatures (optional)")


class SearchBestCitiesRequest(BaseModel):
    person: NatalChartRequest = Field(..., description="Базовые данные натальной карты")
    goal_key: Optional[str] = Field("career_and_business", description="Ключ цели (love_and_marriage, career_and_business, relocation_and_home, education_and_spirituality, health_and_vitality, wealth_and_money)")
    top_n: Optional[int] = Field(5, description="Количество лучших городов")
    country_codes: Optional[List[str]] = Field(None, description="Список ISO кодов стран для фильтрации (например ['RU', 'US'])")

