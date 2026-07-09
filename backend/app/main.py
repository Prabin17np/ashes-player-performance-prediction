"""
app/main.py

FastAPI application entry point for the Ashes Cricket Player Performance
Prediction backend.
Run with:
 Run with:
source .venv/bin/activate
uvicorn backend.app.main:app --reload

(from the project root, where both `backend/` and `ml/` are importable
as Python packages.)
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api import health, model,players, prediction, simulation
from backend.app.config import get_settings
from backend.app.utils.exceptions import register_exception_handlers

settings = get_settings()

# Idempotent: only configures the root logger if it has no handlers yet,
# so importing the pipeline modules below (which configure their own
# logging at import time) doesn't result in duplicate log lines. See
# series_simulator.py's own logging setup for the same pattern.
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        handlers=[logging.StreamHandler()],
    )
else:
    logging.getLogger().setLevel(settings.log_level)

log = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    version=settings.api_version,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(health.router)
app.include_router(players.router)
app.include_router(prediction.router)
app.include_router(simulation.router)
app.include_router(model.router)

log.info(f"{settings.app_name} ({settings.api_version}) ready")