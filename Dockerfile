FROM python:3.11-slim

WORKDIR /app

# На всякий случай выключаем режим require-hashes, если он включён в окружении
ENV PIP_REQUIRE_HASHES=0
ENV PIP_NO_CACHE_DIR=1

COPY requirements.txt /app/requirements.txt

# Обновим pip (иногда важно для wheel выбора)
RUN pip install --upgrade pip \
 && pip install -r /app/requirements.txt

COPY . /app

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
