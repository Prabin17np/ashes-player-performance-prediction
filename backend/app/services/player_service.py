"""
app/services/player_service.py
Service layer backing ``GET /players``.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from ml.build_prediction_features import load_historical_data
from backend.app.schemas.player import PlayerSummary

log = logging.getLogger(__name__)


def list_players(historical_path: Optional[Path] = None) -> list[PlayerSummary]:
   
    kwargs: dict[str, Any] = {}
    if historical_path is not None:
        kwargs["path"] = historical_path

    # as_of_date=pd.Timestamp.max is a read-everything trick: the
    # pipeline's own load_historical_data filters to rows strictly
    # before as_of_date, so the maximum possible timestamp effectively
    # returns the whole historical dataset without this service needing
    # its own "give me everything" code path.
    historical_df = load_historical_data(pd.Timestamp.max, **kwargs)

    if historical_df.empty:
        log.warning("Historical dataset is empty; returning no players.")
        return []

    sorted_df = historical_df.sort_values("Match_Date")
    latest_team_by_player = sorted_df.groupby("Player")["Team"].last()

    players = [
        PlayerSummary(name=player, team=team)
        for player, team in latest_team_by_player.sort_index().items()
    ]

    log.info(f"Listed {len(players)} distinct player(s) from the historical dataset.")
    return players