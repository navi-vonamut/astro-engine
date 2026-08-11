# app/engine/analyzers/astro_goals_matrix.py
from typing import Dict, Any

"""
Astrological Goals Matrix for Astrocartography (ACG) and Local Space (LS).
Maps user intents to specific astrological planets and angles.

Keys:
- target_planets: Planets whose lines and azimuths we search for.
- target_angles: Angles (ASC, DSC, MC, IC, Zenith) where the intersection gives the maximum score.
- avoid_hard_aspects_from: "Malefics". If the target planet has a natal square/opposition 
  from these planets, the algorithm lowers the priority of this line (Safety Check).
"""

ASTRO_GOALS_MATRIX: Dict[str, Dict[str, Any]] = {
    "love_and_marriage": {
        "name": "Love and Relationships",
        "description": "Finding a partner, starting a family, harmonizing personal life and marriage.",
        "target_planets": ["Venus", "Jupiter", "Juno", "Moon"],
        "target_angles": ["DSC", "ASC"],  # Descendant line is primary for partnerships
        "avoid_hard_aspects_from": ["Saturn", "Pluto", "Uranus"]  # Avoid abuse, coldness, and sudden breakups
    },
    "career_and_business": {
        "name": "Career, Business, and Scale",
        "description": "Professional growth, starting a business, fame, scaling projects.",
        "target_planets": ["Sun", "Jupiter", "Pluto", "Mars"],
        "target_angles": ["MC", "Zenith"],  # Midheaven and Zenith for status and career
        "avoid_hard_aspects_from": ["Neptune", "Saturn"]  # Avoid illusions, fraud, and severe blocks
    },
    "relocation_and_home": {
        "name": "Home, Family, and Relocation",
        "description": "Finding a comfortable place to live, buying real estate, peace of mind.",
        "target_planets": ["Moon", "Venus", "Ceres", "Jupiter"],
        "target_angles": ["IC", "ASC"],  # Imum Coeli (IC) for foundation, home, and roots
        "avoid_hard_aspects_from": ["Mars", "Uranus", "Pluto"]  # Avoid conflicts, destruction, and stress
    },
    "education_and_spirituality": {
        "name": "Education, Inspiration, and Spirituality",
        "description": "Higher education, spiritual practices, writing books, retreats.",
        "target_planets": ["Mercury", "Jupiter", "Neptune", "Uranus"],
        "target_angles": ["MC", "ASC", "Zenith"], 
        "avoid_hard_aspects_from": []  # For education, crisis planets can sometimes provide deep focus
    },
    "health_and_vitality": {
        "name": "Health, Sports, and Energy",
        "description": "Recovery, active recreation, boosting vitality.",
        "target_planets": ["Sun", "Mars", "Jupiter"],
        "target_angles": ["ASC"],  # Ascendant is responsible for the physical body
        "avoid_hard_aspects_from": ["Saturn", "Neptune", "Pluto"]  # Avoid chronic diseases and exhaustion
    },
    "wealth_and_money": {
        "name": "Finance and Investments",
        "description": "Attracting capital, investments, increasing personal income.",
        "target_planets": ["Venus", "Jupiter", "Pluto"],
        "target_angles": ["MC", "ASC", "Zenith"],
        "avoid_hard_aspects_from": ["Saturn", "Neptune"]  # Avoid debts and financial losses
    }
}

def get_goal_profile(goal_key: str) -> Dict[str, Any]:
    """Returns the goal profile. Defaults to career/success if the key is not found."""
    return ASTRO_GOALS_MATRIX.get(goal_key, ASTRO_GOALS_MATRIX["career_and_business"])