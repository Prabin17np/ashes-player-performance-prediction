"""
feature_engineering.py

Leakage-safe feature engineering pipeline for Test batting-performance
prediction (England/Australia batters, all opponents), built to support
future Ashes-series simulation.

Pipeline
1. Load raw batting dataset.
2. Sort chronologically (Player -> Match_Date -> Match_ID -> Innings_Number).
3. Engineer career, recent-form, opponent, country-specific-opponent,
   venue, team, and match-context features (Runs itself is left untouched
   as the target column).
4. Validate the engineered dataset (structure + leakage checks).
5. Save the final ML-ready dataset and log a run summary.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

# Configuration
INPUT_PATH = Path("output/batting_dataset.csv")
OUTPUT_PATH = Path("output/final_ml_dataset.csv")
LOG_PATH = Path("logs/feature_engineering.log")

SORT_COLUMNS = ["Player", "Match_Date", "Match_ID", "Innings_Number"]

RECENT_FORM_WINDOWS = [3, 5, 10]
STRIKE_RATE_WINDOWS = [5, 10]
CONSISTENCY_WINDOW = 10

# Mirrors config.py's TEAM_RECENT_MATCH_WINDOW; kept as a local constant so
# this module doesn't need a new cross-file dependency.
TEAM_RECENT_FORM_WINDOW = 5

REQUIRED_INPUT_COLUMNS = [
    "Match_ID", "Match_Date", "Player", "Team", "Opponent", "Venue",
    "Runs", "Balls_Faced", "Innings_Number", "Batting_Position",
    "Is_Dismissed", "Dismissal_Kind", "Toss_Winner", "Toss_Decision",
    "Match_Result", "Winning_Team", "Margin",
]

# Venue -> country mapping. Unmatched venues resolve to "Unknown" rather
# than raising, so an incomplete table never breaks a pipeline run.
VENUE_COUNTRY: dict[str, str] = {
    "Lord's": "England",
    "The Oval": "England",
    "Kennington Oval": "England",
    "Old Trafford": "England",
    "Headingley": "England",
    "Edgbaston": "England",
    "Trent Bridge": "England",
    "Sophia Gardens": "England",
    "Riverside Ground": "England",
    "Melbourne Cricket Ground": "Australia",
    "MCG": "Australia",
    "Sydney Cricket Ground": "Australia",
    "SCG": "Australia",
    "Adelaide Oval": "Australia",
    "The Gabba": "Australia",
    "Bellerive Oval": "Australia",
    "Perth Stadium": "Australia",
    "WACA Ground": "Australia",
    "Manuka Oval": "Australia",
}

# The model target is the current innings' own Runs value -- known at
# load time for every row, so (unlike the old next-innings design) it
# never needs to be derived or have rows dropped to compute it.
TARGET_COLUMN = "Runs"

ID_COLUMNS = ["Match_ID", "Match_Date", "Player", "Team", "Opponent", "Innings_Number"]

CAREER_FEATURES = [
    "career_innings", "career_runs", "career_average", "career_highest_score",
    "career_centuries", "career_fifties", "career_strike_rate",
]
RECENT_FORM_FEATURES = (
    [f"last_{w}_average" for w in RECENT_FORM_WINDOWS]
    + [f"last_{w}_strike_rate" for w in STRIKE_RATE_WINDOWS]
    + ["recent_consistency_score"]
)
CURRENT_OPPONENT_FEATURES = [
    "runs_vs_current_opponent", "innings_vs_current_opponent",
    "average_vs_current_opponent", "strike_rate_vs_current_opponent",
    "dismissal_rate_vs_current_opponent",
    "centuries_vs_current_opponent", "fifties_vs_current_opponent",
]
COUNTRY_OPPONENT_FEATURES = [
    "runs_vs_australia", "average_vs_australia", "innings_vs_australia",
    "runs_vs_england", "average_vs_england", "innings_vs_england",
]
VENUE_FEATURES = [
    "runs_at_venue", "innings_at_venue", "average_at_venue",
    "strike_rate_at_venue", "venue_scoring_difficulty",
]
TEAM_FEATURES = [
    "team_batting_strength", "team_recent_form", "opponent_bowling_strength",
]
# NOTE: toss_decision intentionally excluded -- see module docstring and
# add_match_context_features().
MATCH_CONTEXT_FEATURES = [
    "batting_position", "venue", "venue_country", "innings_number",
    "opponent", "home_or_away",
]

FEATURE_COLUMNS = (
    CAREER_FEATURES
    + RECENT_FORM_FEATURES
    + CURRENT_OPPONENT_FEATURES
    + COUNTRY_OPPONENT_FEATURES
    + VENUE_FEATURES
    + TEAM_FEATURES
    + MATCH_CONTEXT_FEATURES
)

# Raw columns that describe the *current* innings' outcome and must never
# appear as model inputs. Runs is included here because it is now the
# TARGET_COLUMN itself -- it must be excluded from FEATURE_COLUMNS just
# like every other post-innings-outcome column.
LEAKAGE_SOURCE_COLUMNS = [
    "Runs", "Balls_Faced", "Is_Dismissed", "Dismissal_Kind",
    "Match_Result", "Winning_Team", "Margin",
]

_SUPPORTED_STATS = {"mean", "sum", "count"}

# Logging

def setup_logging(log_path: Path = LOG_PATH) -> logging.Logger:
    """Configure a logger that writes to both console and a log file."""
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("feature_engineering")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(message)s"
    )

    file_handler = logging.FileHandler(log_path, mode="w")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger


log = setup_logging()


# Leakage-safe aggregation primitives

def _shifted_expanding_stat(
    sorted_df: pd.DataFrame,
    group_cols: list[str],
    value_col: str,
    stat: str,
) -> pd.Series:
    """Expanding aggregate over history strictly BEFORE the current row.

    shift(1) is applied inside each group before expanding(), which is the
    leakage boundary: the current row's own value never contributes to its
    own feature.
    """
    if stat not in _SUPPORTED_STATS:
        raise ValueError(f"Unsupported stat '{stat}'; expected one of {_SUPPORTED_STATS}")

    def _leakage_safe(group: pd.Series) -> pd.Series:
        history = group.shift(1).expanding()
        return getattr(history, stat)()

    return sorted_df.groupby(group_cols)[value_col].transform(_leakage_safe)


def _shifted_rolling_stat(
    sorted_df: pd.DataFrame,
    group_cols: list[str],
    value_col: str,
    window: int,
    stat: str,
    min_periods: int = 1,
) -> pd.Series:
    """Rolling aggregate over the last `window` rows strictly BEFORE the
    current row (same shift(1) leakage boundary as above)."""
    if stat not in _SUPPORTED_STATS:
        raise ValueError(f"Unsupported stat '{stat}'; expected one of {_SUPPORTED_STATS}")

    def _leakage_safe(group: pd.Series) -> pd.Series:
        history = group.shift(1).rolling(window=window, min_periods=min_periods)
        return getattr(history, stat)()

    return sorted_df.groupby(group_cols)[value_col].transform(_leakage_safe)


def _shifted_rolling_std(
    sorted_df: pd.DataFrame,
    group_cols: list[str],
    value_col: str,
    window: int,
    min_periods: int = 2,
) -> pd.Series:
    """Rolling standard deviation over history strictly BEFORE the current row."""

    def _leakage_safe(group: pd.Series) -> pd.Series:
        return group.shift(1).rolling(window=window, min_periods=min_periods).std()

    return sorted_df.groupby(group_cols)[value_col].transform(_leakage_safe)


def _shifted_cummax(
    sorted_df: pd.DataFrame,
    group_cols: list[str],
    value_col: str,
) -> pd.Series:
    """Running maximum over history strictly BEFORE the current row."""

    def _leakage_safe(group: pd.Series) -> pd.Series:
        return group.shift(1).cummax()

    return sorted_df.groupby(group_cols)[value_col].transform(_leakage_safe)


def _shifted_batting_average(
    sorted_df: pd.DataFrame,
    group_cols: list[str],
    window: int | None = None,
) -> pd.Series:
    """previous runs / previous dismissals, expanding or rolling."""
    if window is None:
        runs_sum = _shifted_expanding_stat(sorted_df, group_cols, "Runs", "sum")
        dismissals_sum = _shifted_expanding_stat(sorted_df, group_cols, "Is_Dismissed", "sum")
    else:
        runs_sum = _shifted_rolling_stat(sorted_df, group_cols, "Runs", window, "sum")
        dismissals_sum = _shifted_rolling_stat(sorted_df, group_cols, "Is_Dismissed", window, "sum")
    return runs_sum / dismissals_sum.replace(0, np.nan)


def _shifted_strike_rate(
    sorted_df: pd.DataFrame,
    group_cols: list[str],
    window: int | None = None,
) -> pd.Series:
    """(previous runs / previous balls faced) * 100, expanding or rolling.

    Rows with missing Balls_Faced are excluded from both numerator and
    denominator so they don't silently distort the ratio.
    """
    balls_known = sorted_df["Balls_Faced"].notna()
    masked = sorted_df.assign(_sr_runs=sorted_df["Runs"].where(balls_known))

    if window is None:
        runs_sum = _shifted_expanding_stat(masked, group_cols, "_sr_runs", "sum")
        balls_sum = _shifted_expanding_stat(masked, group_cols, "Balls_Faced", "sum")
    else:
        runs_sum = _shifted_rolling_stat(masked, group_cols, "_sr_runs", window, "sum")
        balls_sum = _shifted_rolling_stat(masked, group_cols, "Balls_Faced", window, "sum")

    return (runs_sum / balls_sum.replace(0, np.nan)) * 100


def _country_history_stats(
    sorted_df: pd.DataFrame,
    country_label: str,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Career runs / average / innings-count against a specific opponent
    country, visible on EVERY row (not only rows played against that
    country), carried forward in chronological order per player.

    Non-matching rows contribute zero rather than NaN to the running totals
    (they simply add no history vs. that country), which lets a plain
    cumulative sum persist the last known value across unrelated fixtures
    without needing a separate forward-fill step.
    """
    is_country = sorted_df["Opponent"].eq(country_label)

    # Explicit float coercion guards against object-dtype cumsum failures
    # regardless of how Runs/Is_Dismissed arrived (bool, string, etc.).
    indicator = is_country.astype(float)
    runs_masked = sorted_df["Runs"].astype(float).where(is_country, 0.0)
    dismissed_masked = sorted_df["Is_Dismissed"].astype(float).where(is_country, 0.0)

    player_group = sorted_df["Player"]

    shifted_indicator = indicator.groupby(player_group).shift(1).fillna(0.0)
    shifted_runs = runs_masked.groupby(player_group).shift(1).fillna(0.0)
    shifted_dismissed = dismissed_masked.groupby(player_group).shift(1).fillna(0.0)

    innings_count = shifted_indicator.groupby(player_group).cumsum()
    runs_sum = shifted_runs.groupby(player_group).cumsum()
    dismissed_sum = shifted_dismissed.groupby(player_group).cumsum()

    average = (runs_sum / dismissed_sum.replace(0, np.nan)).where(innings_count > 0)

    return runs_sum, average, innings_count

# Pipeline steps

def load_dataset(path: Path = INPUT_PATH) -> pd.DataFrame:
    """Load the raw batting dataset and parse Match_Date."""
    if not path.exists():
        raise FileNotFoundError(f"Input dataset not found at '{path}'.")

    df = pd.read_csv(path)

    missing_cols = [c for c in REQUIRED_INPUT_COLUMNS if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Input dataset is missing required column(s): {missing_cols}")

    df["Match_Date"] = pd.to_datetime(df["Match_Date"])

    # Defensive dtype coercion -- CSVs are notorious for turning booleans
    # into strings ("True"/"False") or leaving numeric columns as object
    # dtype, which silently breaks groupby().cumsum() downstream even
    # though .expanding()/.rolling() tolerate it.
    df["Is_Dismissed"] = (
        df["Is_Dismissed"]
        .replace({"True": True, "False": False, "true": True, "false": False})
        .astype(bool)
        .astype(int)
    )
    df["Runs"] = pd.to_numeric(df["Runs"], errors="coerce")
    df["Balls_Faced"] = pd.to_numeric(df["Balls_Faced"], errors="coerce")
    df["Batting_Position"] = pd.to_numeric(df["Batting_Position"], errors="coerce")

    log.info(f"Loaded {len(df):,} rows, {df['Player'].nunique():,} unique players")
    return df


def sort_chronologically(df: pd.DataFrame) -> pd.DataFrame:
    """Sort by Player -> Match_Date -> Match_ID -> Innings_Number and reset
    the index so downstream groupby/transform operations align cleanly."""
    return df.sort_values(SORT_COLUMNS).reset_index(drop=True)


def add_career_features(df: pd.DataFrame) -> pd.DataFrame:
    """Career-to-date features, all computed strictly before the current row."""
    df = df.copy()
    group_cols = ["Player"]

    df["career_innings"] = _shifted_expanding_stat(df, group_cols, "Runs", "count")
    df["career_runs"] = _shifted_expanding_stat(df, group_cols, "Runs", "sum").fillna(0)
    df["career_average"] = _shifted_batting_average(df, group_cols)
    df["career_highest_score"] = _shifted_cummax(df, group_cols, "Runs").fillna(0)
    df["career_strike_rate"] = _shifted_strike_rate(df, group_cols)

    indicators = df.assign(
        _is_century=(df["Runs"] >= 100).astype(int),
        _is_fifty=((df["Runs"] >= 50) & (df["Runs"] < 100)).astype(int),
    )
    df["career_centuries"] = _shifted_expanding_stat(indicators, group_cols, "_is_century", "sum").fillna(0)
    df["career_fifties"] = _shifted_expanding_stat(indicators, group_cols, "_is_fifty", "sum").fillna(0)

    log.info(f"add_career_features: added {len(CAREER_FEATURES)} features")
    return df


def add_recent_form_features(df: pd.DataFrame) -> pd.DataFrame:
    """Rolling recent-form features using only previous innings."""
    df = df.copy()
    group_cols = ["Player"]

    for window in RECENT_FORM_WINDOWS:
        df[f"last_{window}_average"] = _shifted_batting_average(df, group_cols, window=window)

    for window in STRIKE_RATE_WINDOWS:
        df[f"last_{window}_strike_rate"] = _shifted_strike_rate(df, group_cols, window=window)

    rolling_std = _shifted_rolling_std(df, group_cols, "Runs", window=CONSISTENCY_WINDOW)
    df["recent_consistency_score"] = 1 / (1 + rolling_std)

    log.info(f"add_recent_form_features: added {len(RECENT_FORM_FEATURES)} features")
    return df


def add_opponent_features(df: pd.DataFrame) -> pd.DataFrame:
    """Player-vs-current-opponent history, all excluding the current innings."""
    df = df.copy()
    ordered = df.sort_values(["Player", "Opponent", "Match_Date", "Match_ID", "Innings_Number"])
    group_cols = ["Player", "Opponent"]

    df["runs_vs_current_opponent"] = _shifted_expanding_stat(ordered, group_cols, "Runs", "sum").reindex(df.index)
    df["innings_vs_current_opponent"] = _shifted_expanding_stat(ordered, group_cols, "Runs", "count").reindex(df.index)
    df["average_vs_current_opponent"] = _shifted_batting_average(ordered, group_cols).reindex(df.index)
    df["strike_rate_vs_current_opponent"] = _shifted_strike_rate(ordered, group_cols).reindex(df.index)
    df["dismissal_rate_vs_current_opponent"] = (
        _shifted_expanding_stat(ordered, group_cols, "Is_Dismissed", "mean").reindex(df.index)
    )

    indicators = ordered.assign(
        _is_century=(ordered["Runs"] >= 100).astype(int),
        _is_fifty=((ordered["Runs"] >= 50) & (ordered["Runs"] < 100)).astype(int),
    )
    df["centuries_vs_current_opponent"] = (
        _shifted_expanding_stat(indicators, group_cols, "_is_century", "sum").reindex(df.index).fillna(0)
    )
    df["fifties_vs_current_opponent"] = (
        _shifted_expanding_stat(indicators, group_cols, "_is_fifty", "sum").reindex(df.index).fillna(0)
    )

    log.info(f"add_opponent_features: added {len(CURRENT_OPPONENT_FEATURES)} features")
    return df


def add_country_opponent_features(df: pd.DataFrame) -> pd.DataFrame:
    """Career history against Australia / England specifically, visible on
    every row regardless of who the current opponent is."""
    df = df.copy()
    ordered = df.sort_values(SORT_COLUMNS)

    for country in ("Australia", "England"):
        runs_sum, average, innings_count = _country_history_stats(ordered, country)
        suffix = country.lower()
        df[f"runs_vs_{suffix}"] = runs_sum.reindex(df.index)
        df[f"average_vs_{suffix}"] = average.reindex(df.index)
        df[f"innings_vs_{suffix}"] = innings_count.reindex(df.index)

    log.info(f"add_country_opponent_features: added {len(COUNTRY_OPPONENT_FEATURES)} features")
    return df


def add_venue_features(df: pd.DataFrame) -> pd.DataFrame:
    """Player-at-venue history: how this player has performed at this
    specific ground before, all computed strictly before the current row.

    venue_scoring_difficulty (the venue's general run-scoring character,
    across all players/teams) is added separately in add_team_features,
    since it isn't a per-player quantity.
    """
    df = df.copy()
    ordered = df.sort_values(["Player", "Venue", "Match_Date", "Match_ID", "Innings_Number"])
    group_cols = ["Player", "Venue"]

    df["runs_at_venue"] = _shifted_expanding_stat(ordered, group_cols, "Runs", "sum").reindex(df.index)
    df["innings_at_venue"] = _shifted_expanding_stat(ordered, group_cols, "Runs", "count").reindex(df.index)
    df["average_at_venue"] = _shifted_batting_average(ordered, group_cols).reindex(df.index)
    df["strike_rate_at_venue"] = _shifted_strike_rate(ordered, group_cols).reindex(df.index)

    # Same underlying count as innings_at_venue, exposed under the more
    # descriptive name requested in the feature spec.
    df["venue_experience"] = df["innings_at_venue"]

    log.info("add_venue_features: added runs_at_venue, innings_at_venue, "
             "average_at_venue, strike_rate_at_venue, venue_experience")
    return df


def _build_innings_totals(df: pd.DataFrame) -> pd.DataFrame:
    """Collapse player-level rows into one row per (Match_ID, Team,
    Innings_Number) -- the actual team innings total -- as the basis for
    team- and venue-level aggregates that are properties of the innings as
    a whole, not of any single player."""
    totals = (
        df.groupby(
            ["Match_ID", "Team", "Opponent", "Innings_Number", "Match_Date", "Venue"],
            as_index=False,
        )["Runs"]
        .sum()
        .rename(columns={"Runs": "team_innings_runs"})
    )
    return totals.sort_values(["Match_Date", "Match_ID", "Innings_Number"]).reset_index(drop=True)


def add_team_features(df: pd.DataFrame) -> pd.DataFrame:
   
    totals = _build_innings_totals(df)

    totals["team_batting_strength"] = _shifted_expanding_stat(
        totals, ["Team"], "team_innings_runs", "mean"
    )
    totals["team_recent_form"] = _shifted_rolling_stat(
        totals, ["Team"], "team_innings_runs", window=TEAM_RECENT_FORM_WINDOW, stat="mean"
    )
    totals["opponent_bowling_strength"] = _shifted_expanding_stat(
        totals, ["Opponent"], "team_innings_runs", "mean"
    )
    totals["venue_scoring_difficulty"] = _shifted_expanding_stat(
        totals, ["Venue"], "team_innings_runs", "mean"
    )

    merge_cols = ["Match_ID", "Team", "Innings_Number"]
    new_cols = [
        "team_batting_strength", "team_recent_form",
        "opponent_bowling_strength", "venue_scoring_difficulty",
    ]
    df = df.merge(totals[merge_cols + new_cols], on=merge_cols, how="left")

    log.info("add_team_features: added team_batting_strength, team_recent_form, "
             "opponent_bowling_strength, venue_scoring_difficulty")
    return df


def _lookup_venue_country(venue: pd.Series) -> pd.Series:
    """Map Venue -> country using VENUE_COUNTRY; unmatched venues -> 'Unknown'."""
    return venue.map(VENUE_COUNTRY).fillna("Unknown")


def _classify_home_away(team: pd.Series, venue_country: pd.Series) -> pd.Series:
    """England player at an England venue = Home, at an Australia venue =
    Away (and symmetrically for Australia players). Unknown venues = Neutral."""
    result = pd.Series("Away", index=team.index)
    result = result.mask(venue_country.eq(team), "Home")
    result = result.mask(venue_country.eq("Unknown"), "Neutral")
    return result


def add_match_context_features(df: pd.DataFrame) -> pd.DataFrame:
  
    df = df.copy()

    df["batting_position"] = df["Batting_Position"]
    df["venue"] = df["Venue"]
    df["innings_number"] = df["Innings_Number"]
    df["opponent"] = df["Opponent"]

    venue_country = _lookup_venue_country(df["Venue"])
    df["venue_country"] = venue_country
    df["home_or_away"] = _classify_home_away(df["Team"], venue_country)

    log.info(f"add_match_context_features: added {len(MATCH_CONTEXT_FEATURES)} features")
    return df


# Validation

def validate_dataset(df: pd.DataFrame) -> bool:
    """Structural, statistical, and leakage validation of the final dataset.

    Returns True if all checks pass; logs a warning (rather than raising)
    for any failed check so a single issue doesn't hide the rest of the
    report.
    """
    log.info("-- Dataset validation --")
    passed = True

    def check(condition: bool, ok_msg: str, fail_msg: str) -> None:
        nonlocal passed
        if condition:
            log.info(f"  OK    {ok_msg}")
        else:
            log.warning(f"  FAIL  {fail_msg}")
            passed = False

    # target
    check(TARGET_COLUMN in df.columns, "Target column ('Runs') present", "Target column missing!")

    check(
        TARGET_COLUMN not in FEATURE_COLUMNS,
        "Target ('Runs') is not present in FEATURE_COLUMNS",
        "Target ('Runs') unexpectedly present in FEATURE_COLUMNS!",
    )

    check(
        "next_innings_runs" not in df.columns,
        "next_innings_runs column absent (old target design fully removed)",
        "next_innings_runs column unexpectedly present in the dataset!",
    )

    # structure 
    missing_features = [c for c in FEATURE_COLUMNS if c not in df.columns]
    check(not missing_features, "All required feature columns present",
          f"Missing feature column(s): {missing_features}")

    dup_count = df.duplicated(subset=["Match_ID", "Player", "Innings_Number"]).sum()
    check(dup_count == 0, "One row per player innings (no duplicate Match_ID + Player + Innings_Number)",
          f"{dup_count} duplicate row(s) found")

    # numeric sanity
    numeric_feature_cols = [
        c for c in FEATURE_COLUMNS if c in df.columns and pd.api.types.is_numeric_dtype(df[c])
    ]
    inf_counts = {
        col: int(np.isinf(df[col]).sum())
        for col in numeric_feature_cols
        if np.isinf(df[col]).any()
    }
    check(not inf_counts, "No infinite values in any numeric feature column",
          f"Infinite values found: {inf_counts}")

    check((df["Runs"] >= 0).all(), "Runs non-negative",
          f"{(df['Runs'] < 0).sum()} negative Runs value(s)")

    count_like_cols = [
        "career_innings", "career_runs", "career_highest_score",
        "career_centuries", "career_fifties",
        "runs_vs_current_opponent", "innings_vs_current_opponent",
        "centuries_vs_current_opponent", "fifties_vs_current_opponent",
        "runs_vs_australia", "innings_vs_australia",
        "runs_vs_england", "innings_vs_england",
        "runs_at_venue", "innings_at_venue", "venue_experience",
    ]
    for col in count_like_cols:
        if col not in df.columns:
            continue
        valid = df[col].dropna()
        check((valid >= 0).all(), f"'{col}' non-negative",
              f"{(valid < 0).sum()} negative value(s) in '{col}'")

    # leakage checks 
    leaked_in_features = [c for c in LEAKAGE_SOURCE_COLUMNS if c in FEATURE_COLUMNS]
    check(not leaked_in_features, "No current-innings outcome column used as a feature",
          f"Leakage columns found in FEATURE_COLUMNS: {leaked_in_features}")

    check("toss_decision" not in FEATURE_COLUMNS,
          "Toss_Decision excluded from features (unknowable for future series)",
          "toss_decision unexpectedly present in FEATURE_COLUMNS")

    ordered = df.sort_values(SORT_COLUMNS)
    first_rows = ordered.groupby("Player").head(1)

    non_zero_first = int((first_rows["career_innings"] != 0).sum())
    check(non_zero_first == 0,
          "Every player's first recorded innings has career_innings == 0 (shift(1) verified -- "
          "no future/current information used)",
          f"{non_zero_first} player(s) show non-zero career_innings on their first innings")

    zero_runs_first = int((first_rows["career_runs"] != 0).sum())
    check(zero_runs_first == 0,
          "Every player's first recorded innings has career_runs == 0",
          f"{zero_runs_first} player(s) show non-zero career_runs on their first innings")

    non_null_avg_first = int(first_rows["career_average"].notna().sum())
    check(non_null_avg_first == 0,
          "Every player's first recorded innings has a null career_average",
          f"{non_null_avg_first} player(s) show a non-null career_average on their first innings")

    recent_form_cols = [c for c in RECENT_FORM_FEATURES if c in first_rows.columns]
    non_null_recent_first = {
        c: int(first_rows[c].notna().sum())
        for c in recent_form_cols
        if first_rows[c].notna().sum() > 0
    }
    check(not non_null_recent_first,
          "All recent-form features are null on every player's first innings",
          f"Non-null recent-form values found on first innings: {non_null_recent_first}")

    #  monotonic non-decreasing career counters
    monotonic_issues = {}
    for col in ["career_innings", "career_runs", "career_centuries", "career_fifties"]:
        if col not in df.columns:
            continue
        diffs = ordered.groupby("Player")[col].diff()
        n_decreases = int((diffs < 0).sum())
        if n_decreases:
            monotonic_issues[col] = n_decreases
    check(not monotonic_issues,
          "Career counters (innings/runs/centuries/fifties) never decrease within a player",
          f"Decreasing counter values found: {monotonic_issues}")

    for col in ["Match_ID", "Match_Date", "Player", "Team", "Innings_Number", "Opponent", "Venue"]:
        nulls = df[col].isna().sum()
        check(nulls == 0, f"No nulls in '{col}'", f"{nulls} null(s) in '{col}'")

    log.info("------------------------")
    return passed

# Save + reporting

def save_dataset(df: pd.DataFrame, path: Path = OUTPUT_PATH) -> None:
    """Persist the final ML-ready dataset to CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    log.info(f"Saved final ML dataset -> '{path}' ({len(df):,} rows, {len(df.columns)} columns)")


def report_summary(df: pd.DataFrame) -> None:
    """Print dataset shape, feature list, and target statistics."""
    print("\n=== Final Dataset Shape ===")
    print(df.shape)

    print("\n=== Feature List ===")
    for col in FEATURE_COLUMNS:
        print(f"  - {col}")

    print(f"\n=== Target Statistics: {TARGET_COLUMN} ===")
    target = df[TARGET_COLUMN]
    stats = {
        "count": int(target.count()),
        "mean": target.mean(),
        "median": target.median(),
        "std": target.std(),
        "min": target.min(),
        "max": target.max(),
    }
    for name, value in stats.items():
        print(f"  {name:<8}: {value}")


# Main

def main() -> None:
    log.info("Starting feature engineering pipeline")

    raw_df = load_dataset(INPUT_PATH)
    input_rows = len(raw_df)

    df = sort_chronologically(raw_df)

    # NOTE: no target-creation step here. Runs is already the target and
    # is already present on every row from load_dataset() -- unlike the
    # old next_innings_runs design, no rows need to be dropped to compute
    # it, so every player's most recent recorded innings is retained.

    df = add_career_features(df)
    df = add_recent_form_features(df)
    df = add_opponent_features(df)
    df = add_country_opponent_features(df)
    df = add_venue_features(df)
    df = add_team_features(df)
    df = add_match_context_features(df)

    is_valid = validate_dataset(df)

    save_dataset(df, OUTPUT_PATH)

    log.info(f"Input rows: {input_rows:,} | Output rows: {len(df):,} | Feature count: {len(FEATURE_COLUMNS)}")
    log.info("No rows were dropped for target-creation purposes (Runs is the target and "
             "is known for every row).")
    if not is_valid:
        log.warning("Validation had failures -- review logs before using this dataset for modeling.")

    report_summary(df)


if __name__ == "__main__":
    main()