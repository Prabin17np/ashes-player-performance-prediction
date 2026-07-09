
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
   

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Ashes Cricket Player Performance Prediction API"
    api_version: str = "v1"
    log_level: str = "INFO"

    cors_allow_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"]
    )

    # Deliberately Optional[Path], defaulting to None -- see module
    # docstring. Forwarded as-is to generate_prediction()/simulate_series(),
    # never used by this backend to read data or load models directly.
    historical_path: Optional[Path] = Field(default=None, alias="HISTORICAL_DATA_PATH")
    models_dir: Optional[Path] = Field(default=None, alias="MODELS_DIR")

    default_allow_debutants: bool = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
  
    return Settings()