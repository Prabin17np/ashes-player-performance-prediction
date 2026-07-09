
from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd

import ml.train_model as tm
from ml.build_prediction_features import (
    PredictionRequest,
    generate_prediction_features,
    predict_with_saved_artifacts,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger(__name__)

# MODELS_DIR is read off `train_model` (the module, imported as `tm`)
# rather than imported by name, purely so the same import statement above
# can also give us access to `tm._bool_to_float` for the pickle workaround
# below -- both need the same module object, not two separate imports of
# the same file.
MODELS_DIR = tm.MODELS_DIR


def _register_main_scope_helpers() -> None:
   
    sys.modules["__main__"]._bool_to_float = tm._bool_to_float

# PART 1 -- Prediction Result

@dataclass(frozen=True)
class PredictionResult:
   
    player: str
    team: str
    opponent: str
    venue: str
    match_date: pd.Timestamp
    innings_number: int
    predicted_runs: float
    batting_position: Optional[int] = None

    def as_dict(self) -> dict[str, Any]:
        """Return this result as a plain, JSON/CSV-friendly dictionary,
        with `match_date` rendered as an ISO date string rather than a
        `pd.Timestamp` object."""
        return {
            "Player": self.player,
            "Team": self.team,
            "Opponent": self.opponent,
            "Venue": self.venue,
            "Match_Date": self.match_date.date().isoformat(),
            "Innings_Number": self.innings_number,
            "Batting_Position": self.batting_position,
            "Predicted_Runs": self.predicted_runs,
        }

    def __str__(self) -> str:
        return (
            f"{self.player} ({self.team} vs {self.opponent}, {self.venue}, "
            f"{self.match_date.date()}, innings {self.innings_number}) -> "
            f"Predicted Runs: {self.predicted_runs:.2f}"
        )

# PART 2 -- Extract a scalar from predict_with_saved_artifacts' output
def _extract_scalar_prediction(prediction: np.ndarray) -> float:
    
    flattened = np.asarray(prediction).ravel()
    if flattened.size != 1:
        raise ValueError(
            f"Expected exactly one prediction for a single-row feature vector, "
            f"got {flattened.size}. Verify the feature vector passed to "
            "predict_with_saved_artifacts has exactly one row."
        )
    return float(flattened[0])


# PART 3 -- Public entry point

def generate_prediction(
    request: PredictionRequest,
    models_dir: Path = MODELS_DIR,
    historical_path: Optional[Path] = None,
    extra_history: Optional[pd.DataFrame] = None,
    allow_debut: bool = False,
) -> PredictionResult:
    
    log.info(
        f"Generating prediction for '{request.player}' "
        f"({request.team} vs {request.opponent} at {request.venue}, "
        f"{request.match_date.date()}, innings {request.innings_number})"
    )

    # Pure pass-through: only forward historical_path/extra_history if the
    # caller actually supplied them, so generate_prediction_features's own
    # defaults apply otherwise. No logic, computation, or default value is
    # duplicated here. allow_debut is always forwarded explicitly since its
    # own default already matches generate_prediction_features's default.
    feature_kwargs: dict[str, Any] = {"allow_debut": allow_debut}
    if historical_path is not None:
        feature_kwargs["historical_path"] = historical_path
    if extra_history is not None:
        feature_kwargs["extra_history"] = extra_history

    feature_vector = generate_prediction_features(request, **feature_kwargs)

    # Must run before predict_with_saved_artifacts unpickles anything --
    # see _register_main_scope_helpers' docstring for why this is needed.
    _register_main_scope_helpers()

    log.info(f"Loading saved artifacts and predicting from '{models_dir}'")
    raw_prediction = predict_with_saved_artifacts(feature_vector, models_dir=models_dir)
    predicted_runs = _extract_scalar_prediction(raw_prediction)

    result = PredictionResult(
        player=request.player,
        team=request.team,
        opponent=request.opponent,
        venue=request.venue,
        match_date=request.match_date,
        innings_number=request.innings_number,
        predicted_runs=round(predicted_runs, 2),
        batting_position=request.batting_position,
    )

    log.info(f"Prediction complete: {result}")
    return result


# Demo entry point

def main() -> None:
    """
    Small runnable demonstration: predicts runs for a hypothetical future
    Ashes innings and prints a clean result. Replace the example request
    below with real inputs for an actual prediction.
    """
    example_request = PredictionRequest(
        player="BA Stokes",
        team="England",
        opponent="Australia",
        venue="Lord's",
        match_date="2027-06-18",   # hypothetical 2027 Ashes
        innings_number=1,
        batting_position=6,  # omit / pass None if not yet finalised
    )

    result = generate_prediction(example_request)

    print("\nPrediction result:")
    for key, value in result.as_dict().items():
        print(f"  {key:<15}: {value}")


if __name__ == "__main__":
    main()