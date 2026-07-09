"""
app/api/simulation.py

``POST /simulate``run a full series simulation through the existing
ML pipeline's ``simulate_series()``.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, status

from backend.app.config import Settings, get_settings
from backend.app.schemas.simulation import (
    PlayerSeriesSummarySchema,
    PredictionResultSchema,
    SimulateRequest,
    SimulateResponse,
)
from backend.app.services import simulation_service

log = logging.getLogger(__name__)
router = APIRouter(tags=["simulation"])


@router.post(
    "/simulate",
    response_model=SimulateResponse,
    status_code=status.HTTP_200_OK,
    summary="Simulate an entire series of fixtures",
)
def simulate(
    payload: SimulateRequest, settings: Settings = Depends(get_settings)
) -> SimulateResponse:
   
    log.info(f"POST /simulate for {len(payload.fixtures)} fixture(s)")

    result = simulation_service.simulate(
        payload,
        default_allow_debutants=settings.default_allow_debutants,
        historical_path=settings.historical_path,
        models_dir=settings.models_dir,
    )

    predictions_out = [
        PredictionResultSchema(
            player=p.player,
            team=p.team,
            opponent=p.opponent,
            venue=p.venue,
            match_date=p.match_date.date(),
            innings_number=p.innings_number,
            batting_position=p.batting_position,
            predicted_runs=p.predicted_runs,
        )
        for p in result.predictions
    ]

    summaries_out = [
        PlayerSeriesSummarySchema(
            player=s.player,
            team=s.team,
            matches=s.matches,
            innings=s.innings,
            total_runs=s.total_runs,
            batting_average=s.batting_average,
            highest_score=s.highest_score,
            lowest_score=s.lowest_score,
            fifties=s.fifties,
            centuries=s.centuries,
            predicted_scores=s.predicted_scores,
        )
        for s in result.player_summaries
    ]

    return SimulateResponse(
        predictions=predictions_out,
        player_summaries=summaries_out,
        team_totals=result.team_totals,
    )