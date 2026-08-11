# app/engine/analyzers/astro_urbanistics.py
"""
Astro-Urbanistics Mapping: Maps astrological planets and life goals 
to OpenStreetMap (OSM) Overpass QL tag queries (amenity, shop, leisure, tourism, etc.).
"""

from typing import Dict, List, Tuple, Any

PLANET_OSM_TAGS: Dict[str, List[Tuple[str, str]]] = {
    "Venus": [
        ("amenity", "cafe|beauty_salon|spa"),
        ("shop", "beauty|hairdresser|jewelry|clothes|florist|boutique|perfumery"),
        ("tourism", "gallery"),
        ("leisure", "park|garden")
    ],
    "Mars": [
        ("amenity", "fitness_centre|car_wash"),
        ("shop", "sports|car_repair|hardware|car"),
        ("leisure", "fitness_centre|sports_centre|pitch|track|sports_hall")
    ],
    "Jupiter": [
        ("amenity", "bank|university|restaurant|lawyer|embassy|courthouse"),
        ("tourism", "hotel")
    ],
    "Moon": [
        ("amenity", "bakery|cafe|kindergarten|childcare|fountain"),
        ("shop", "bakery|supermarket|convenience"),
        ("leisure", "park|garden|playground")
    ],
    "Sun": [
        ("amenity", "townhall|public_building|theatre|arts_centre"),
        ("tourism", "artwork|attraction|gallery|museum")
    ],
    "Mercury": [
        ("amenity", "library|post_office|school|college|coworking_space"),
        ("shop", "books|stationery|newsagent|mobile_phone|computer")
    ],
    "Saturn": [
        ("amenity", "townhall|archive|court|police"),
        ("tourism", "museum"),
        ("historic", "monument|building|memorial|castle")
    ],
    "Uranus": [
        ("amenity", "planetarium|coworking_space"),
        ("shop", "electronics|computer|mobile_phone")
    ],
    "Neptune": [
        ("amenity", "pharmacy|pub|bar|cinema|nightclub|spa"),
        ("leisure", "swimming_pool|water_park")
    ],
    "Pluto": [
        ("railway", "subway_entrance|station"),
        ("shop", "tattoo"),
        ("amenity", "bank|waste_disposal")
    ]
}

GOAL_TO_PLANET_MAPPING: Dict[str, str] = {
    "love": "Venus",
    "love_and_marriage": "Venus",
    "relationship": "Venus",
    "romance": "Venus",
    "свидание": "Venus",
    "любовь": "Venus",
    "красота": "Venus",

    "sport": "Mars",
    "fitness": "Mars",
    "health_and_vitality": "Mars",
    "спорт": "Mars",
    "фитнес": "Mars",
    "тренировка": "Mars",

    "money": "Jupiter",
    "wealth": "Jupiter",
    "career": "Jupiter",
    "wealth_and_money": "Jupiter",
    "career_and_business": "Jupiter",
    "деньги": "Jupiter",
    "бизнес": "Jupiter",
    "карьера": "Jupiter",
    "финансы": "Jupiter",

    "home": "Moon",
    "family": "Moon",
    "relocation_and_home": "Moon",
    "дом": "Moon",
    "семья": "Moon",
    "уют": "Moon",

    "study": "Mercury",
    "education": "Mercury",
    "learning": "Mercury",
    "education_and_spirituality": "Mercury",
    "учеба": "Mercury",
    "обучение": "Mercury",
    "книги": "Mercury",

    "art": "Sun",
    "culture": "Sun",
    "культура": "Sun",
    "творчество": "Sun",

    "relax": "Neptune",
    "rest": "Neptune",
    "отдых": "Neptune",
    "кино": "Neptune"
}

def resolve_target_planet(key: str) -> str:
    """Resolve input string (planet name or goal key) to standard Planet Name."""
    key_clean = key.strip().lower()
    
    # Check if exact planet name match (case-insensitive)
    for planet_name in PLANET_OSM_TAGS.keys():
        if planet_name.lower() == key_clean:
            return planet_name
            
    # Check goal mapping
    if key_clean in GOAL_TO_PLANET_MAPPING:
        return GOAL_TO_PLANET_MAPPING[key_clean]
        
    # Default to Venus if unknown
    return "Venus"

def get_osm_tags_for_planet(planet_name: str) -> List[Tuple[str, str]]:
    """Return OSM tag filters for planet."""
    return PLANET_OSM_TAGS.get(planet_name, PLANET_OSM_TAGS["Venus"])
