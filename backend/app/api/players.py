"""
app/api/players.py

``GET /players``list every player available in the historical
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from backend.app.config import Settings, get_settings
from backend.app.schemas.player import PlayerSummary
from backend.app.services import player_service

log = logging.getLogger(__name__)
router = APIRouter(tags=["players"])


@router.get(
    "/players",
    response_model=list[PlayerSummary],
    summary="List every player available in the historical dataset",
)
def get_players(settings: Settings = Depends(get_settings)) -> list[PlayerSummary]:
    log.info("GET /players")
    return player_service.list_players(historical_path=settings.historical_path)