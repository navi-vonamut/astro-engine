FROM python:3.11-slim

WORKDIR /app

# Отключаем кэш pip и хэши для ускорения сборки в dev-режиме
ENV PIP_REQUIRE_HASHES=0
ENV PIP_NO_CACHE_DIR=1
# Python не будет буферизировать stdout/stderr (логи видны сразу)
ENV PYTHONUNBUFFERED=1

# 1. Установка системных зависимостей
# build-essential необходим для сборки библиотек с C-расширениями (numpy, pyswisseph)
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt

# 2. Установка Python-зависимостей
RUN pip install --upgrade pip \
 && pip install -r /app/requirements.txt

# 3. Копируем исходный код проекта
COPY . /app

# 4. 🔥 ГЕНЕРАЦИЯ БАЗЫ ГОРОДОВ ПРИ СБОРКЕ
# Мы запускаем скрипт как модуль.
# Предполагается путь: app/geo/scripts/generate_cities.py
# Убедись, что в папках app, geo и scripts есть пустые файлы __init__.py
RUN python -m app.geo.scripts.generate_cities

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]