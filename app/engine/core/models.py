from dataclasses import dataclass

VALID_HOUSE_SYSTEMS = {'A', 'B', 'C', 'D', 'F', 'H', 'I', 'i', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y'}

def sanitize_house_system(h_sys: str) -> str:
    if not h_sys:
        return "P"
    h_sys = str(h_sys).strip()
    if h_sys == "E":
        return "A"
    if h_sys in VALID_HOUSE_SYSTEMS:
        return h_sys
    for valid in VALID_HOUSE_SYSTEMS:
        if valid.lower() == h_sys.lower():
            return valid
    return "P"

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

    def __post_init__(self):
        object.__setattr__(self, "house_system", sanitize_house_system(self.house_system))