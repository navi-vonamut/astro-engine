from dataclasses import dataclass

@dataclass(frozen=True)
class BirthInput:
    name: str
    date: str
    time: str
    tz: str
    lat: float
    lon: float
    house_system: str = "P"
    node_type: str = "true"