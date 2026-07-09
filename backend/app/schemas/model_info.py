from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelInfoResponse(BaseModel):

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "model_name": "Ashes Player Performance Predictor",
                "algorithm": "CatBoostRegressor",
                "training_samples": 6652,
                "features": 40,
                "cv_mae": 23.97,
                "cv_rmse": 33.95,
                "cv_r2": 0.106,
                "test_mae": 23.63,
                "test_rmse": 34.29,
                "test_r2": 0.123,
            }
        }
    )

    model_name: str = Field(..., description="Name of the prediction model.")

    algorithm: str = Field(..., description="Selected machine learning algorithm.")

    training_samples: int = Field(..., description="Number of historical innings used for training.")

    features: int = Field(..., description="Number of input features.")

    cv_mae: float = Field(..., description="Cross-validation Mean Absolute Error.")

    cv_rmse: float = Field(..., description="Cross-validation Root Mean Squared Error.")

    cv_r2: float = Field(..., description="Cross-validation R² score.")

    test_mae: float = Field(..., description="Test Mean Absolute Error.")

    test_rmse: float = Field(..., description="Test Root Mean Squared Error.")

    test_r2: float = Field(..., description="Test R² score.")