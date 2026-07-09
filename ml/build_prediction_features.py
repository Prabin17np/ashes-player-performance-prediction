from __future__ import annotations

import logging
from dataclasses import dataclass
from difflib import get_close_matches
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd

import ml.config as config
import ml.feature_engineering as fe
import ml.train_model as tm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger(__name__)

# Prefix used to build a synthetic Match_ID for the future innings.

_PREDICTION_MATCH_ID_PREFIX = "PREDICTION"

# PART 1 -- Prediction Request (inputs + fail-fast validation)

@dataclass(frozen=True)
class PredictionRequest:
    
    player: str
    team: str
    opponent: str
    venue: str
    match_date: str | pd.Timestamp
    innings_number: int
    batting_position: Optional[int] = None

    def __post_init__(self) -> None:
        if not str(self.player).strip():
            raise ValueError("PredictionRequest.player must be a non-empty string.")
        if not str(self.venue).strip():
            raise ValueError("PredictionRequest.venue must be a non-empty string.")

        if self.team not in config.TARGET_TEAMS:
            raise ValueError(
                f"PredictionRequest.team '{self.team}' is not one of the modelled "
                f"Ashes teams {sorted(config.TARGET_TEAMS)}."
            )
        if self.opponent == self.team:
            raise ValueError("PredictionRequest.opponent must differ from team.")
        if self.opponent not in config.VALID_TEST_NATIONS:
            raise ValueError(
                f"PredictionRequest.opponent '{self.opponent}' is not a recognised "
                f"Test nation {sorted(config.VALID_TEST_NATIONS)}."
            )
        if self.innings_number not in (1, 2, 3, 4):
            raise ValueError(
                f"PredictionRequest.innings_number must be 1-4, got {self.innings_number}."
            )
        if self.batting_position is not None and not (1 <= self.batting_position <= 11):
            raise ValueError(
                f"PredictionRequest.batting_position must be 1-11 or None, "
                f"got {self.batting_position}."
            )

        # Normalize match_date to a real Timestamp now, fail-fast if unparsable,
        # so every downstream function can assume a proper datetime already.
        try:
            parsed_date = pd.to_datetime(self.match_date)
        except (ValueError, TypeError) as exc:
            raise ValueError(
                f"PredictionRequest.match_date '{self.match_date}' could not be parsed "
                "as a date."
            ) from exc
        # dataclass is frozen -- use object.__setattr__ to normalize in place.
        object.__setattr__(self, "match_date", parsed_date)


# PART 2 -- Load historical data, strictly before the prediction date

def load_historical_data(
    as_of_date: pd.Timestamp,
    path: Path = config.PARSER_OUTPUT_FILE,
    extra_history: pd.DataFrame | None = None,
) -> pd.DataFrame:
   
    df = fe.load_dataset(path=path)

    if extra_history is not None and not extra_history.empty:
        missing_cols = [c for c in df.columns if c not in extra_history.columns]
        if missing_cols:
            raise ValueError(
                f"extra_history is missing required column(s): {missing_cols}. "
                "It must use the same raw schema as the parser output."
            )
        df = pd.concat([df, extra_history[df.columns]], ignore_index=True)

    historical = df[df["Match_Date"] < as_of_date].copy()

    if historical.empty:
        log.warning(
            f"No historical rows found strictly before {as_of_date.date()} -- "
            "every engineered feature for this prediction will be NaN (correct "
            "behaviour for a debut/first-ever fixture, but verify this is expected)."
        )
    else:
        log.info(
            f"Loaded {len(historical):,} historical row(s) strictly before "
            f"{as_of_date.date()} (of {len(df):,} total rows available)."
        )

    # Defensive assertion -- must always hold given the filter above; a
    # failure here would indicate a dtype/comparison bug, not bad input data.
    assert (historical["Match_Date"] < as_of_date).all(), (
        "Internal error: historical data filter let a non-earlier row through."
    )

    return historical

# PART 3 -- Build the synthetic future row

def _build_future_row(
    request: PredictionRequest,
    reference_columns: pd.Index,
    synthetic_match_id: str,
) -> pd.DataFrame:
    
    placeholders: dict[str, Any] = {col: np.nan for col in reference_columns}

    placeholders.update({
        "Match_ID": synthetic_match_id,
        "Match_Date": request.match_date,
        "Player": request.player,
        "Team": request.team,
        "Opponent": request.opponent,
        "Venue": request.venue,
        "Innings_Number": request.innings_number,
        "Batting_Position": (
            request.batting_position if request.batting_position is not None else np.nan
        ),
        # --- Unknowable-for-a-future-series placeholders (see docstring
        # above and PredictionRequest's docstring). Never used as
        # anything but a value that gets shifted away from its own row.
        "Toss_Winner": np.nan,
        "Toss_Decision": np.nan,
        "Match_Result": np.nan,
        "Winning_Team": np.nan,
        "Margin": np.nan,
        "Runs": np.nan,
        "Balls_Faced": np.nan,
        "Is_Dismissed": 0,
        "Dismissal_Kind": np.nan,
        "Dismissal_Bowler": np.nan,
        "Dismissal_Fielders": np.nan,
    })

    return pd.DataFrame([placeholders], columns=reference_columns)

# PART 4 -- Assemble historical + future, run the shared feature pipeline

def _assemble_and_engineer(
    historical_df: pd.DataFrame,
    future_row: pd.DataFrame,
) -> pd.DataFrame:
    
    combined = pd.concat([historical_df, future_row], ignore_index=True)

    combined = fe.sort_chronologically(combined)
    combined = fe.add_career_features(combined)
    combined = fe.add_recent_form_features(combined)
    combined = fe.add_opponent_features(combined)
    combined = fe.add_country_opponent_features(combined)
    combined = fe.add_venue_features(combined)
    combined = fe.add_team_features(combined)
    combined = fe.add_match_context_features(combined)

    return combined


# PART 5 -- Select the final, training-ordered feature vector

def _select_prediction_feature_vector(
    engineered_df: pd.DataFrame,
    synthetic_match_id: str,
) -> pd.DataFrame:
    
    X, _y, spec = tm.prepare_features(engineered_df, target_col=tm.TARGET_COL)

    expected_n = len(fe.FEATURE_COLUMNS)
    if len(spec.all_feature_cols) != expected_n:
        raise ValueError(
            f"Expected {expected_n} predictor columns to match "
            "feature_engineering.FEATURE_COLUMNS, got {len(spec.all_feature_cols)}. "
            "The upstream feature_engineering.py or train_model.py column layout "
            "may have changed -- investigate before trusting this feature vector."
        )

    match_mask = engineered_df["Match_ID"] == synthetic_match_id
    if match_mask.sum() != 1:
        raise RuntimeError(
            f"Expected exactly one row with synthetic Match_ID "
            f"'{synthetic_match_id}', found {match_mask.sum()}. This indicates "
            "either a Match_ID collision with real historical data, or the "
            "future row was dropped somewhere in the pipeline -- investigate "
            "before trusting this feature vector."
        )
    future_index = engineered_df.index[match_mask][0]

    feature_vector = X.loc[[future_index]].reset_index(drop=True)

    return feature_vector


def _validate_player_exists(
    player: str,
    df: pd.DataFrame,
    *,
    allow_debut: bool = False,
) -> None:
    """
    Ensure the requested player exists in the historical dataset.

    Parameters
    player : str
        The player name to validate.
    df : pd.DataFrame
        Historical dataframe to check against.
    allow_debut : bool, default False
        If False, an unrecognised player raises ValueError (guards against
        typos). If True, an unrecognised player is treated as a legitimate
        debutant: a warning is logged (still surfacing close-match
        suggestions in case it *was* a typo) and the function returns
        normally instead of raising.

    Raises
    ValueError
        If the player is not found and allow_debut is False.
    """
    players = sorted(df["Player"].dropna().unique())

    if player in players:
        return

    suggestions = get_close_matches(player, players, n=5, cutoff=0.6)

    message = f"Player '{player}' not found in the historical dataset."

    if suggestions:
        message += f"\nDid you mean: {suggestions}?"

    if allow_debut:
        log.warning(message)
        return

    raise ValueError(message)

# PART 6 -- Public entry point

def generate_prediction_features(
    request: PredictionRequest,
    historical_path: Path = config.PARSER_OUTPUT_FILE,
    extra_history: pd.DataFrame | None = None,
    allow_debut: bool = False,
) -> pd.DataFrame:
    """
    Build one prediction-ready feature vector for a future innings.

    request : PredictionRequest
        Validated pre-match facts for the innings to predict.
    historical_path : Path
        Where to load real historical rows from (parser output by default).
    extra_history : pd.DataFrame | None
        Optional additional raw-schema rows (e.g. simulated innings fed
        forward by series_simulator.py) treated as real history for this
        prediction.
    allow_debut : bool, default False
        Forwarded unchanged to `_validate_player_exists`. False (the
        original, stricter behaviour) raises on any player not found in
        history, which is what catches typos. True treats an unrecognised
        player as a legitimate debutant: a warning is logged instead of
        raising. Kept as an explicit opt-in per call rather than a
        module-wide toggle, since most single-shot predictions still want
        typo protection -- only a series simulator sweeping a full,
        pre-agreed squad across many innings needs debutants to pass
        through without raising.

    Raises
    ValueError
        If `request.player` is not found in history and `allow_debut` is
        False.
    """
    
    log.info(f"Generating prediction feature vector for '{request.player}' "
              f"({request.team} vs {request.opponent} at {request.venue}, "
              f"{request.match_date.date()})")

    historical_df = load_historical_data(
        request.match_date, path=historical_path, extra_history=extra_history
    )

    _validate_player_exists(
        request.player,
        historical_df,
        allow_debut=allow_debut,
    )

    synthetic_match_id = (
        f"{_PREDICTION_MATCH_ID_PREFIX}_{request.player}_{request.match_date.date()}"
        f"_innings{request.innings_number}"
    )
    future_row = _build_future_row(request, historical_df.columns, synthetic_match_id)

    engineered_df = _assemble_and_engineer(historical_df, future_row)
    feature_vector = _select_prediction_feature_vector(engineered_df, synthetic_match_id)

    log.info(f"Generated feature vector with {feature_vector.shape[1]} predictor columns.")
    return feature_vector


# PART 7 (optional convenience) -- Predict directly from saved artifacts

def predict_with_saved_artifacts(
    feature_vector: pd.DataFrame,
    models_dir: Path = tm.MODELS_DIR,
) -> np.ndarray:
   
    import joblib

    preprocessor_path = models_dir / "preprocessor.pkl"
    model_path = models_dir / "best_model.pkl"

    if not preprocessor_path.exists() or not model_path.exists():
        raise FileNotFoundError(
            f"Expected saved artifacts at '{preprocessor_path}' and '{model_path}' "
            "-- run train_model.py first."
        )

    preprocessor = joblib.load(preprocessor_path)
    model = joblib.load(model_path)

    transformed = preprocessor.transform(feature_vector)
    return model.predict(transformed)


# Demo entry point

def main() -> None:
    """
    Small runnable demonstration: builds a feature vector for a
    hypothetical future Ashes innings and prints it. Replace the example
    request below with real inputs for an actual prediction.
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

    feature_vector = generate_prediction_features(example_request)

    print("\nPrediction-ready feature vector:")
    print(feature_vector.to_string(index=False))

    print(f"\nShape: {feature_vector.shape[0]} row x {feature_vector.shape[1]} columns")


if __name__ == "__main__":
    main()