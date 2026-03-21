import swisseph as swe

# === 1. ПЛАНЕТЫ И ТОЧКИ (Маппинг для Swiss Ephemeris) ===
SWISSEPH_OBJECTS = {
    'Sun': swe.SUN, 
    'Moon': swe.MOON, 
    'Mercury': swe.MERCURY,
    'Venus': swe.VENUS, 
    'Mars': swe.MARS, 
    'Jupiter': swe.JUPITER,
    'Saturn': swe.SATURN, 
    'Uranus': swe.URANUS, 
    'Neptune': swe.NEPTUNE,
    'Pluto': swe.PLUTO,
    'Chiron': swe.CHIRON,
    'Mean_Lilith': swe.MEAN_APOG,
    'True_North_Lunar_Node': swe.TRUE_NODE,
    'Ceres': getattr(swe, 'CERES', 17),     
    'Pallas': getattr(swe, 'PALLAS', 18),   
    'Juno': getattr(swe, 'JUNO', 19),       
    'Vesta': getattr(swe, 'VESTA', 20)
}

# === 2. АСПЕКТЫ И ОРБИСЫ ===
# Правила: Угол -> (Название, Орбис_для_Планет, Орбис_для_Фиктивных)
ASPECT_RULES = {
    0:   ("conjunction", 8.0, 2.5),
    60:  ("sextile", 6.0, 2.0),
    90:  ("square", 8.0, 2.5),
    120: ("trine", 8.0, 2.5),
    180: ("opposition", 8.0, 2.5),
    30:  ("semisextile", 1.5, 1.0),
    45:  ("semisquare", 1.5, 1.0),
    72:  ("quintile", 1.5, 1.0),
    135: ("sesquiquadrate", 1.5, 1.0),
    144: ("biquintile", 1.5, 1.0),
    150: ("quincunx", 2.0, 1.5)
}

# Точки, для которых орбис всегда должен быть строгим (маленьким)
STRICT_POINTS = [
    "True_North_Lunar_Node", "True_South_Lunar_Node", "Mean_Lilith", 
    "Fortune", "Vertex", "Ascendant", "Descendant", "Medium_Coeli", "Imum_Coeli"
]

# === 3. ЗНАКИ ЗОДИАКА ===
SIGNS_FULL = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
SIGNS_SHORT = ["Ari", "Tau", "Gem", "Can", "Leo", "Vir", "Lib", "Sco", "Sag", "Cap", "Aqu", "Pis"]

# === 4. ДОМА (для Kerykeion) ===
KERYKEION_HOUSES = [
    "first_house", "second_house", "third_house", "fourth_house", 
    "fifth_house", "sixth_house", "seventh_house", "eighth_house", 
    "ninth_house", "tenth_house", "eleventh_house", "twelfth_house"
]

# === 5. УПРАВИТЕЛИ ЗНАКОВ ===
# 0:Овен, 1:Телец, 2:Близнецы, 3:Рак, 4:Лев, 5:Дева
# 6:Весы, 7:Скорпион, 8:Стрелец, 9:Козерог, 10:Водолей, 11:Рыбы
SIGN_RULERS_BY_ID = {
    0: "Mars",
    1: "Venus",
    2: "Mercury",
    3: "Moon",
    4: "Sun",
    5: "Mercury",
    6: "Venus",
    7: "Pluto",      # Современный управитель Скорпиона
    8: "Jupiter",
    9: "Saturn",
    10: "Uranus",    # Современный управитель Водолея
    11: "Neptune"    # Современный управитель Рыб
}

# Целевые точки для парсинга в натале (Связка: "Имя в Kerykeion" -> "Наш Label")
TARGET_POINTS_BASE = [
    ("Sun", "Sun"), ("Moon", "Moon"), ("Mercury", "Mercury"), 
    ("Venus", "Venus"), ("Mars", "Mars"), ("Jupiter", "Jupiter"), 
    ("Saturn", "Saturn"), ("Uranus", "Uranus"), ("Neptune", "Neptune"), 
    ("Pluto", "Pluto"), ("Chiron", "Chiron"),
    ("Mean_Lilith", "Mean_Lilith"),
    ("Ceres", "Ceres"), ("Pallas", "Pallas"), 
    ("Juno", "Juno"), ("Vesta", "Vesta")
]