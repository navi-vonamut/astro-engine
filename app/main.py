from __future__ import annotations

from fastapi import FastAPI

from .routes.natal import router as natal_router
from .routes.predict import router as predict_router
from .routes.synastry import router as synastry_router
from .routes.horary import router as horary_router
from .routes.solar import router as solar_router 
from .routes.geo import router as geo_router
from .routes.lunar import router as lunar_router
from .routes.progression import router as progression_router
from .routes.composite import router as composite_router
from .routes.electional import router as electional_router
from .routes.content import router as content_router

app = FastAPI(title="astro-engine", version="0.2.0")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/meta")
def meta():
    return {"engine": "kerykeion", "engine_version": "5.6.0"}

app.include_router(natal_router)
app.include_router(predict_router)
app.include_router(synastry_router)
app.include_router(horary_router)
app.include_router(solar_router)
app.include_router(geo_router)  
app.include_router(lunar_router)
app.include_router(progression_router)
app.include_router(composite_router)
app.include_router(electional_router)
app.include_router(content_router)