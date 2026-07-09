
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PlayerSummary(BaseModel):
   
    model_config = ConfigDict(
        json_schema_extra={
            "example": {"name": "JE Root", "team": "England"},
        }
    )

    name: str = Field(..., description="Player's name as it appears in the historical dataset.")
    team: str = Field(..., description="Team the player is associated with.")