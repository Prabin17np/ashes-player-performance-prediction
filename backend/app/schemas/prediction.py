
from __future__ import annotations

from datetime import date
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class PredictRequest(BaseModel):
   
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "player": "JE Root",
                "team": "England",
                "opponent": "Australia",
                "venue": "Lord's",
                "match_date": "2027-06-18",
                "innings_number": 1,
                "batting_position": 4,
            }
        }
    )

    player: str = Field(..., min_length=1, description="Batter's name.")
    team: str = Field(..., min_length=1, description="The batter's team for this innings.")
    opponent: str = Field(..., min_length=1, description="The opposing team for this match.")
    venue: str = Field(..., min_length=1, description="Ground name.")
    match_date: date = Field(..., description="Date of the match (ISO 8601).")
    innings_number: int = Field(..., description="Which innings of the match this is for (1-4).")
    batting_position: Optional[int] = Field(
        default=None, description="Batting order position, if already finalised."
    )


class PredictResponse(BaseModel):
 
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "player": "JE Root",
                "team": "England",
                "opponent": "Australia",
                "venue": "Lord's",
                "match_date": "2027-06-18",
                "innings_number": 1,
                "batting_position": 4,
                "predicted_runs": 44.47,
                "confidence": None,
                "features": None,
            }
        }
    )

    player: str
    team: str
    opponent: str
    venue: str
    match_date: date
    innings_number: int
    batting_position: Optional[int] = None
    predicted_runs: float
    confidence: Optional[float] = Field(
        default=None,
        description="Reserved; not currently produced by generate_prediction().",
    )
    features: Optional[dict[str, Any]] = Field(
        default=None,
        description="Reserved; not currently returned by generate_prediction().",
    )