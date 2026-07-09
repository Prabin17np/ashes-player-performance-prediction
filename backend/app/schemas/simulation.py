"""
app/schemas/simulation.py
Request/response schemas for the ``POST /simulate`` endpoint.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class FixtureRequest(BaseModel):

    player: str = Field(..., min_length=1)
    team: str = Field(..., min_length=1)
    opponent: str = Field(..., min_length=1)
    venue: str = Field(..., min_length=1)
    match_date: date
    innings_number: int
    batting_position: Optional[int] = None


class SimulateRequest(BaseModel):

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "fixtures": [
                    {
                        "player": "JE Root",
                        "team": "England",
                        "opponent": "Australia",
                        "venue": "Lord's",
                        "match_date": "2027-06-18",
                        "innings_number": 1,
                        "batting_position": 4,
                    }
                ],
                "allow_debutants": True,
            }
        }
    )

    fixtures: list[FixtureRequest] = Field(..., min_length=1)
    allow_debutants: Optional[bool] = Field(
        default=None,
        description="Defaults to Settings.default_allow_debutants if omitted.",
    )


class PredictionResultSchema(BaseModel):
    
    player: str
    team: str
    opponent: str
    venue: str
    match_date: date
    innings_number: int
    batting_position: Optional[int] = None
    predicted_runs: float


class PlayerSeriesSummarySchema(BaseModel):
   
    player: str
    team: str
    matches: int
    innings: int
    total_runs: float
    batting_average: float
    highest_score: float
    lowest_score: float
    fifties: int
    centuries: int
    predicted_scores: list[float]


class SimulateResponse(BaseModel):
   
    predictions: list[PredictionResultSchema]
    player_summaries: list[PlayerSeriesSummarySchema]
    team_totals: dict[str, float]