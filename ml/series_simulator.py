
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd

from ml.build_prediction_features import PredictionRequest, load_historical_data
from ml.predict_player_performance import PredictionResult, generate_prediction

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger(__name__)

# Prefix used to build a synthetic Match_ID for each simulated innings row
# appended to extra_history. Distinct from build_prediction_features.py's
# own "PREDICTION" prefix (which is transient, per-call, and never
# persisted into history) so the two can never collide.
_SIMULATED_MATCH_ID_PREFIX = "SIMULATED"

# The raw schema build_prediction_features.load_historical_data() requires
# of extra_history: every column present in the real parser output
# (config.REQUIRED_COLUMNS), in a fixed order. Declared once here so every
# simulated row is built consistently and so pd.concat never silently
# reorders or drops a column.
_RAW_SCHEMA_COLUMNS = [
    "Match_ID", "Match_Date", "Player", "Team", "Opponent", "Venue",
    "Toss_Winner", "Toss_Decision", "Match_Result", "Winning_Team", "Margin",
    "Runs", "Balls_Faced", "Innings_Number", "Batting_Position",
    "Is_Dismissed", "Dismissal_Kind", "Dismissal_Bowler", "Dismissal_Fielders",
]

# Thresholds mirroring standard cricket scoring milestones, used only for
# the series-level century/fifty counts below.
_CENTURY_THRESHOLD = 100
_FIFTY_THRESHOLD = 50


# PART 1 -- Series Fixture (one scheduled, not-yet-played innings)

@dataclass(frozen=True)
class SeriesFixture:
    
    player: str
    team: str
    opponent: str
    venue: str
    match_date: str | pd.Timestamp
    innings_number: int
    batting_position: Optional[int] = None

    def to_request(self) -> PredictionRequest:
       
        return PredictionRequest(
            player=self.player,
            team=self.team,
            opponent=self.opponent,
            venue=self.venue,
            match_date=self.match_date,
            innings_number=self.innings_number,
            batting_position=self.batting_position,
        )

# PART 2 -- Series-level summaries

@dataclass
class PlayerSeriesSummary:
   
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

    def as_dict(self) -> dict[str, Any]:
        """Plain, CSV/JSON-friendly dictionary representation."""
        return {
            "Player": self.player,
            "Team": self.team,
            "Matches": self.matches,
            "Innings": self.innings,
            "Total_Runs": self.total_runs,
            "Batting_Average": self.batting_average,
            "Highest_Score": self.highest_score,
            "Lowest_Score": self.lowest_score,
            "Fifties": self.fifties,
            "Centuries": self.centuries,
            "Predicted_Scores": self.predicted_scores,
        }

    def format_report(self) -> str:
        """
        Thesis-ready, multi-line report block for this player, e.g.:

            Joe Root
            Predicted innings scores

            44
            67
            ...

            Matches Played : 5
            Innings        : 10
            Total Runs     : 537
            Average        : 53.70
            Highest Score  : 112
            Lowest Score   : 8
            50s            : 5
            100s           : 1

        """
        rule = "=" * 54
        lines = [rule, self.player, rule, "", "Predicted innings scores", ""]
        lines.extend(f"{score:.0f}" for score in self.predicted_scores)
        lines.extend([
            "",
            f"{'Matches Played':<15}: {self.matches}",
            f"{'Innings':<15}: {self.innings}",
            f"{'Total Runs':<15}: {self.total_runs:.0f}",
            f"{'Average':<15}: {self.batting_average:.2f}",
            f"{'Highest Score':<15}: {self.highest_score:.0f}",
            f"{'Lowest Score':<15}: {self.lowest_score:.0f}",
            f"{'50s':<15}: {self.fifties}",
            f"{'100s':<15}: {self.centuries}",
        ])
        return "\n".join(lines)

    def __str__(self) -> str:
        return (
            f"{self.player} ({self.team}): {self.total_runs:.0f} runs in "
            f"{self.innings} innings ({self.matches} match(es)), "
            f"avg {self.batting_average:.2f}, "
            f"{self.centuries} century/ies, {self.fifties} fifty/ies, "
            f"highest {self.highest_score:.0f}, lowest {self.lowest_score:.0f}"
        )


@dataclass(frozen=True)
class SeriesSimulationResult:
    
    predictions: list[PredictionResult]
    simulated_history: pd.DataFrame
    player_summaries: list[PlayerSeriesSummary]
    team_totals: dict[str, float]

    def player_summary(self, player: str) -> Optional[PlayerSeriesSummary]:
        """Look up a single player's summary by name, or None if that
        player was not part of the simulated schedule."""
        for summary in self.player_summaries:
            if summary.player == player:
                return summary
        return None

    def summary_table(self) -> pd.DataFrame:
        """Player summaries as a single DataFrame, ready to print or
        export -- built once, on demand, rather than duplicating this
        data as a stored attribute."""
        return pd.DataFrame([s.as_dict() for s in self.player_summaries])


# PART 3 -- Chronological ordering

def _sort_fixtures_chronologically(fixtures: list[SeriesFixture]) -> list[SeriesFixture]:
    
    return sorted(
        fixtures,
        key=lambda fx: (pd.to_datetime(fx.match_date), fx.innings_number),
    )


# PART 4 -- PredictionResult -> raw-schema history row

def _load_reference_schema(historical_path: Optional[Path]) -> pd.DataFrame:
   
    kwargs: dict[str, Any] = {}
    if historical_path is not None:
        kwargs["path"] = historical_path

    reference = load_historical_data(pd.Timestamp.max, **kwargs)
    return reference[_RAW_SCHEMA_COLUMNS].iloc[0:0].copy()


def _prediction_result_to_history_row(
    result: PredictionResult,
    sequence_number: int,
) -> dict[str, Any]:
    
    synthetic_match_id = (
        f"{_SIMULATED_MATCH_ID_PREFIX}_{result.match_date.date()}"
        f"_{result.team}_vs_{result.opponent}"
        f"_innings{result.innings_number}_{sequence_number}"
    )

    row: dict[str, Any] = {col: np.nan for col in _RAW_SCHEMA_COLUMNS}
    row.update({
        "Match_ID": synthetic_match_id,
        "Match_Date": result.match_date,
        "Player": result.player,
        "Team": result.team,
        "Opponent": result.opponent,
        "Venue": result.venue,
        "Innings_Number": result.innings_number,
        "Batting_Position": (
            result.batting_position if result.batting_position is not None else np.nan
        ),
        "Runs": result.predicted_runs,
        "Is_Dismissed": 0,
    })
    return row

# PART 5 -- Series-level summaries from PredictionResults

def _compute_player_summaries(predictions: list[PredictionResult]) -> list[PlayerSeriesSummary]:

    if not predictions:
        return []

    frame = pd.DataFrame([r.as_dict() for r in predictions])

    summaries: list[PlayerSeriesSummary] = []
    for (player, team), group in frame.groupby(["Player", "Team"], sort=False):
        runs = group["Predicted_Runs"]
        innings = int(len(group))
        total_runs = float(runs.sum())
        # Distinct matches, not innings -- a player bats up to twice per
        # Test, so (Match_Date, Opponent, Venue) is the natural match key
        # within a single player's group (team is constant per the
        # class-level assumption documented on PlayerSeriesSummary).
        matches = int(group[["Match_Date", "Opponent", "Venue"]].drop_duplicates().shape[0])

        summaries.append(PlayerSeriesSummary(
            player=player,
            team=team,
            matches=matches,
            innings=innings,
            total_runs=total_runs,
            batting_average=total_runs / innings,
            highest_score=float(runs.max()),
            lowest_score=float(runs.min()),
            fifties=int(((runs >= _FIFTY_THRESHOLD) & (runs < _CENTURY_THRESHOLD)).sum()),
            centuries=int((runs >= _CENTURY_THRESHOLD).sum()),
            predicted_scores=runs.tolist(),
        ))

    summaries.sort(key=lambda s: s.total_runs, reverse=True)
    return summaries


def _compute_team_totals(predictions: list[PredictionResult]) -> dict[str, float]:
    """Total predicted runs per team, summed directly from
    `predictions` for the same reason as `_compute_player_summaries`."""
    totals: dict[str, float] = {}
    for result in predictions:
        totals[result.team] = totals.get(result.team, 0.0) + result.predicted_runs
    return totals

# PART 6 -- Public entry point

def simulate_series(
    fixtures: list[SeriesFixture],
    historical_path: Optional[Path] = None,
    models_dir: Optional[Path] = None,
    allow_debutants: bool = True,
) -> SeriesSimulationResult:
    
    if not fixtures:
        raise ValueError("simulate_series() requires at least one SeriesFixture.")

    ordered_fixtures = _sort_fixtures_chronologically(fixtures)
    distinct_players = {fx.player for fx in ordered_fixtures}

    log.info(
        f"Starting series simulation: {len(ordered_fixtures)} innings "
        f"across {len(distinct_players)} player(s), "
        f"{ordered_fixtures[0].match_date} -> {ordered_fixtures[-1].match_date}"
    )

    # Forwarded to every generate_prediction() call. Only populated for
    # overrides the caller actually supplied, so generate_prediction's own
    # defaults apply otherwise -- no default value is duplicated here.
    prediction_kwargs: dict[str, Any] = {"allow_debut": allow_debutants}
    if historical_path is not None:
        prediction_kwargs["historical_path"] = historical_path
    if models_dir is not None:
        prediction_kwargs["models_dir"] = models_dir

    # Seeded from the real parser-output dtypes (see _load_reference_schema's
    # docstring) instead of pd.DataFrame(columns=_RAW_SCHEMA_COLUMNS), which
    # had no rows to infer dtypes from and so silently defaulted every
    # column to object -- the root cause of both the dtype-drift bug and
    # the FutureWarning previously raised by pd.concat below.
    simulated_history = _load_reference_schema(historical_path)
    predictions: list[PredictionResult] = []

    for sequence_number, fixture in enumerate(ordered_fixtures, start=1):
        request = fixture.to_request()

        log.info(
            f"[{sequence_number}/{len(ordered_fixtures)}] Predicting "
            f"'{request.player}' ({request.team} vs {request.opponent} at "
            f"{request.venue}, {request.match_date.date()}, "
            f"innings {request.innings_number})"
        )

        result = generate_prediction(
            request,
            extra_history=simulated_history if not simulated_history.empty else None,
            **prediction_kwargs,
        )
        predictions.append(result)

        new_row = _prediction_result_to_history_row(result, sequence_number)
        # Cast the new row to simulated_history's own dtypes before
        # concatenating, so both sides of every concat already agree on
        # dtype -- no empty/all-NA column is left for pandas to guess a
        # result dtype for, which is what removes the FutureWarning as a
        # direct consequence of the dtype fix rather than as a separate
        # suppression.
        new_row_df = pd.DataFrame([new_row], columns=_RAW_SCHEMA_COLUMNS).astype(
            simulated_history.dtypes.to_dict()
        )
        simulated_history = pd.concat([simulated_history, new_row_df], ignore_index=True)

    player_summaries = _compute_player_summaries(predictions)
    team_totals = _compute_team_totals(predictions)

    log.info(
        f"Series simulation complete: {len(predictions)} innings predicted, "
        f"{len(player_summaries)} player summary/ies computed."
    )

    return SeriesSimulationResult(
        predictions=predictions,
        simulated_history=simulated_history,
        player_summaries=player_summaries,
        team_totals=team_totals,
    )

# Demo entry point

def main() -> None:
    example_schedule = [
        SeriesFixture(
            player="BA Stokes", team="England", opponent="Australia",
            venue="Lord's", match_date="2027-06-18",
            innings_number=1, batting_position=6,
        ),
        SeriesFixture(
            player="JE Root", team="England", opponent="Australia",
            venue="Lord's", match_date="2027-06-18",
            innings_number=1, batting_position=4,
        ),
        SeriesFixture(
            player="New Uncapped Player", team="England", opponent="Australia",
            venue="Lord's", match_date="2027-06-18",
            innings_number=1, batting_position=3,
        ),
        SeriesFixture(
            player="BA Stokes", team="England", opponent="Australia",
            venue="The Oval", match_date="2027-07-30",
            innings_number=1, batting_position=6,
        ),
        SeriesFixture(
            player="JE Root", team="England", opponent="Australia",
            venue="The Oval", match_date="2027-07-30",
            innings_number=1, batting_position=4,
        ),
    ]

    result = simulate_series(example_schedule)

    print("\nIndividual innings predictions:")
    for prediction in result.predictions:
        print(f"  {prediction}")

    print("\nPlayer series summaries:\n")
    for summary in result.player_summaries:
        print(summary.format_report())
        print()

    print("Team totals (predicted runs):")
    for team, total in result.team_totals.items():
        print(f"  {team:<12}: {total:.0f}")


if __name__ == "__main__":
    main()