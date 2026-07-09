"""
app/api/model.py

GET /model

Return information about the trained machine learning model.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter

from backend.app.schemas.model_info import ModelInfoResponse
from backend.app.services import model_info_service as model_service

log = logging.getLogger(__name__)

router = APIRouter(tags=["model"])


@router.get(
    "/model",
    response_model=ModelInfoResponse,
    summary="Get information about the trained prediction model",
)
def get_model_info() -> ModelInfoResponse:
    
    log.info("GET /model")
    return model_service.get_model_info()