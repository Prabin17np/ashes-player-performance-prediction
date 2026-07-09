"""
app/services/simulation_service.py
Service layer backing ``POST /simulate``.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

from ml.series_simulator import SeriesFixture, SeriesSimulationResult, simulate_series

from backend.app.schemas.simulation import SimulateRequest

log = logging.getLogger(__name__)


def simulate(
    payload: SimulateRequest,
    default_allow_debutants: bool,
    historical_path: Optional[Path] = None,
    models_dir: Optional[Path] = None,
) -> SeriesSimulationResult:
    
    fixtures = [
        SeriesFixture(
            player=fx.player,
            team=fx.team,
            opponent=fx.opponent,
            venue=fx.venue,
            match_date=fx.match_date,
            innings_number=fx.innings_number,
            batting_position=fx.batting_position,
        )
        for fx in payload.fixtures
    ]

    allow_debutants = (
        payload.allow_debutants if payload.allow_debutants is not None else default_allow_debutants
    )

    log.info(f"Requesting series simulation for {len(fixtures)} fixture(s).")

    # Only forwarded if the caller actually supplied an override, so
    # simulate_series's own defaults apply otherwise.
    kwargs: dict[str, Any] = {"allow_debutants": allow_debutants}
    if historical_path is not None:
        kwargs["historical_path"] = historical_path
    if models_dir is not None:
        kwargs["models_dir"] = models_dir

    result = simulate_series(fixtures, **kwargs)

    log.info(
        f"Series simulation complete: {len(result.predictions)} innings predicted, "
        f"{len(result.player_summaries)} player summary/ies."
    )
    return result