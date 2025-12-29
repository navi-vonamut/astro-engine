from __future__ import annotations

from fastapi import FastAPI

from .routes.natal import router as natal_router
from .routes.predict import router as predict_router
from .routes.synastry import router as synastry_router
from .routes.horary import router as horary_router

app = FastAPI(title="astro-engine", version="0.1.0")


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
