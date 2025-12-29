from __future__ import annotations

from pydantic import BaseModel
import os


class Settings(BaseModel):
    internal_api_key: str = os.getenv("INTERNAL_API_KEY", "")


SETTINGS = Settings()
