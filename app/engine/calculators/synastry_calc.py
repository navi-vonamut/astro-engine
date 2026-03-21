from typing import Any, Dict, List
from kerykeion import AspectsFactory
from app.engine.core.utils import get_house_for_degree

def get_synastry_aspects(subject1, subject2) -> List[Dict[str, Any]]:
    """Рассчитывает аспекты между двумя картами"""
    try:
        res = AspectsFactory.dual_chart_aspects(subject1, subject2)
    except Exception as e:
        print(f"[ENGINE ERROR] AspectsFactory error: {e}")
        return []

    PLANET_WHITELIST = {
        "Sun", "Moon", "Mercury", "Venus", "Mars", 
        "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto",
        "Chiron", "True Node", "Lilith"
    }
    
    ALLOWED_ASPECTS = {"conjunction", "opposition", "square", "trine", "sextile"}
    
    aspects = []
    for a in res.aspects:
        d = a.model_dump(mode="json")
        
        p1_n = d.get("p1_name", "")
        p2_n = d.get("p2_name", "")
        raw_asp = d.get("aspect_name") or d.get("aspect") or ""
        asp_lower = raw_asp.lower()
        orb_raw = d.get("orbit", d.get("orb", 0.0)) 
        orb = float(orb_raw if orb_raw is not None else 0.0)

        if p1_n not in PLANET_WHITELIST or p2_n not in PLANET_WHITELIST:
            continue

        if asp_lower not in ALLOWED_ASPECTS:
            continue

        # Умные орбисы для синастрии
        limit = 3.0
        if "Moon" in p1_n: limit = 8.0  
        elif "Sun" in p1_n: limit = 6.0
        elif p1_n in ["Mercury", "Venus", "Mars"]: limit = 5.0
        elif p1_n in ["Jupiter", "Saturn"]: limit = 4.0
        if any(x in p1_n for x in ["Node", "Lilith", "Chiron"]): limit = 1.5

        if abs(orb) > limit:
            continue

        aspects.append({
            "person1_object": p1_n,
            "aspect": raw_asp.title(),
            "person2_object": p2_n,
            "orb": orb,
        })
        
    return aspects

def calculate_house_overlays(planets: List[Dict], partner_houses: List[Dict]) -> List[Dict]:
    """Рассчитывает попадание планет одного человека в дома партнера"""
    overlays = []
    for p in planets:
        house_in_partner = get_house_for_degree(p["abs_pos"], partner_houses)
        
        # Защита от выхода за пределы массива
        house_sign = ""
        if 1 <= house_in_partner <= len(partner_houses):
            house_sign = partner_houses[house_in_partner - 1]["sign"]
            
        overlays.append({
            "planet": p["name"],
            "in_partner_house": house_in_partner,
            "partner_house_sign": house_sign
        })
    return overlays