"""
app/api/prediction.py

``POST /predict``run a single prediction through the existing ML
pipeline's ``generate_prediction()``.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, status

from backend.app.config import Settings, get_settings
from backend.app.schemas.prediction import PredictRequest, PredictResponse
from backend.app.services import prediction_service

log = logging.getLogger(__name__)
router = APIRouter(tags=["prediction"])


@router.post(
    "/predict",
    response_model=PredictResponse,
    status_code=status.HTTP_200_OK,
    summary="Predict runs for a single future innings",
)
def predict(
    payload: PredictRequest, settings: Settings = Depends(get_settings)
) -> PredictResponse:
    log.info(f"POST /predict for '{payload.player}'")

    result = prediction_service.predict(
        payload,
        historical_path=settings.historical_path,
        models_dir=settings.models_dir,
    )

    return PredictResponse(
        player=result.player,
        team=result.team,
        opponent=result.opponent,
        venue=result.venue,
        match_date=result.match_date.date(),
        innings_number=result.innings_number,
        batting_position=result.batting_position,
        predicted_runs=result.predicted_runs,
    )