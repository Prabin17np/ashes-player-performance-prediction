"""
app/services/prediction_service.py

Service layer backing ``POST /predict``.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

from ml.build_prediction_features import PredictionRequest
from ml.predict_player_performance import PredictionResult, generate_prediction

from backend.app.schemas.prediction import PredictRequest

log = logging.getLogger(__name__)


def predict(
    payload: PredictRequest,
    historical_path: Optional[Path] = None,
    models_dir: Optional[Path] = None,
) -> PredictionResult:
    
    request = PredictionRequest(
        player=payload.player,
        team=payload.team,
        opponent=payload.opponent,
        venue=payload.venue,
        match_date=payload.match_date,
        innings_number=payload.innings_number,
        batting_position=payload.batting_position,
    )

    log.info(
        f"Requesting prediction for '{request.player}' "
        f"({request.team} vs {request.opponent} at {request.venue}, "
        f"{payload.match_date})"
    )

    # Only forwarded if the caller actually supplied an override, so
    # generate_prediction's own defaults apply otherwise -- no default
    # value is duplicated here.
    kwargs: dict[str, Any] = {}
    if historical_path is not None:
        kwargs["historical_path"] = historical_path
    if models_dir is not None:
        kwargs["models_dir"] = models_dir

    result = generate_prediction(request, **kwargs)

    log.info(f"Prediction complete: {result}")
    return result