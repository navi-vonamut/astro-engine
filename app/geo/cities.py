# app/geo/cities.py

import json
from pathlib import Path
from typing import List, Dict

# Путь к JSON (генерируется скриптом выше)
DATA_PATH = Path(__file__).parent / "data" / "major_cities.json"

# Кэш в оперативной памяти
_CITIES_CACHE: List[Dict] = []

def get_major_cities() -> List[Dict]:
    """
    Возвращает список городов из JSON.
    Загружает файл один раз при первом вызове (Singleton pattern).
    """
    global _CITIES_CACHE
    
    if _CITIES_CACHE:
        return _CITIES_CACHE
    
    if not DATA_PATH.exists():
        # Если файла нет (забыли сгенерировать), возвращаем пустой список,
        # чтобы сервис не упал, но в логи пишем warning
        print(f"WARNING: Файл городов не найден: {DATA_PATH}")
        return []
    
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            _CITIES_CACHE = data
            return _CITIES_CACHE
    except Exception as e:
        print(f"ERROR: Ошибка чтения базы городов: {e}")
        return []