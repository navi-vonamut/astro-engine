from __future__ import annotations

from fastapi import Header, HTTPException
from .config import SETTINGS


def verify_internal_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> str:
    if not SETTINGS.internal_api_key:
        raise HTTPException(status_code=500, detail="INTERNAL_API_KEY is not configured")

    if not x_api_key or x_api_key != SETTINGS.internal_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return x_api_key
