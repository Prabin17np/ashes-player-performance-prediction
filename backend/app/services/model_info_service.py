"""
app/services/model_service.py

Service layer backing `GET /model`.
"""

from __future__ import annotations

import logging

from backend.app.schemas.model_info import ModelInfoResponse

log = logging.getLogger(__name__)


def get_model_info() -> ModelInfoResponse:
    """
    Return metadata and evaluation metrics for the trained prediction model.
    """

    log.info("Returning model information.")

    return ModelInfoResponse(
        model_name="Ashes Player Performance Predictor",
        algorithm="CatBoostRegressor",
        training_samples=6652,
        features=40,
        cv_mae=23.97,
        cv_rmse=33.95,
        cv_r2=0.106,
        test_mae=23.63,
        test_rmse=34.29,
        test_r2=0.123,
    )