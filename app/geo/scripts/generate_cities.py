# app/geo/scripts/generate_cities.py

import json
import geonamescache
from pathlib import Path

# Импортируем наш ручной список.
# Обрати внимание: при запуске через python -m, импорт работает от корня
from app.geo.curated_cities import CURATED_HUBS

# Конфигурация
MIN_POPULATION = 80_000  # Фильтр для авто-городов
TOP_LIMIT = 5000          # Сколько всего городов храним

# Путь сохранения: app/geo/data/major_cities.json
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "major_cities.json"

def generate_cities():
    print("🚀 Начинаем генерацию базы городов...")
    
    gc = geonamescache.GeonamesCache()
    cities = gc.get_cities()
    
    # 1. Собираем автоматический список
    auto_cities = []
    for cid, city in cities.items():
        if city['population'] < MIN_POPULATION:
            continue
            
        auto_cities.append({
            "name": city['name'],
            "lat": float(city['latitude']),
            "lon": float(city['longitude']),
            "country": city['countrycode'],
            "population": city['population'],
            "timezone": city['timezone']
        })

    # Сортируем по населению (сначала мегаполисы)
    auto_cities.sort(key=lambda x: x['population'], reverse=True)
    
    # 2. Объединяем списки (Сначала наши Curated, потом Auto)
    # Используем словарь для удаления дубликатов по ключу "Название-Страна"
    
    unique_map = {}
    
    # Сначала добавляем авто-города (они могут быть перезаписаны нашими хабами)
    for c in auto_cities:
        key = f"{c['name']}-{c['country']}"
        unique_map[key] = c
        
    # Теперь принудительно перезаписываем/добавляем наши Хабы
    # Это гарантирует, что координаты и данные наших хабов приоритетнее
    for hub in CURATED_HUBS:
        key = f"{hub['name']}-{hub['country']}"
        unique_map[key] = hub

    # 3. Превращаем обратно в список и обрезаем лишнее
    final_list = list(unique_map.values())
    
    # Еще раз сортируем: Хабы пусть будут вперемешку или можно поднять их вверх.
    # Но для NumPy порядок не важен. Оставим сортировку по населению для красоты JSON.
    final_list.sort(key=lambda x: x.get('population', 0), reverse=True)
    
    # Ограничиваем количество, чтобы не убить фронтенд
    final_list = final_list[:TOP_LIMIT]

    # 4. Сохраняем
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_list, f, ensure_ascii=False, indent=2)
        
    print(f"✅ Успешно сохранено {len(final_list)} городов в {OUTPUT_FILE}")

if __name__ == "__main__":
    generate_cities()