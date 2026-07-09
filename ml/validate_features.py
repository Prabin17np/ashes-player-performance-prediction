import sys
import numpy as np
import pandas as pd

from ml.config import (
    ML_OUTPUT_FILE,
    MAX_PLAUSIBLE_RUNS,
    TARGET_COLUMN,
)

CSV = str(ML_OUTPUT_FILE)

checks = []


def chk(label, result, detail=""):
    status = "OK" if result else "FAIL"
    print(f"[{status}] {label}" + (f" -> {detail}" if detail else ""))
    checks.append(bool(result))


def info(label, detail=""):
    print(f"[i]    {label}" + (f" -> {detail}" if detail else ""))

# Schema

TARGET = TARGET_COLUMN

# Kept in sync with feature_engineering.py's FEATURE_COLUMNS. toss_decision
# is deliberately absent: it's excluded from the pipeline's features because
# it isn't known before a future, not-yet-played series' toss happens.
FEATURE_COLUMNS = [
    "career_innings",
    "career_runs",
    "career_average",
    "career_highest_score",
    "career_centuries",
    "career_fifties",
    "career_strike_rate",

    "last_3_average",
    "last_5_average",
    "last_10_average",
    "last_5_strike_rate",
    "last_10_strike_rate",
    "recent_consistency_score",

    "runs_vs_current_opponent",
    "innings_vs_current_opponent",
    "average_vs_current_opponent",
    "strike_rate_vs_current_opponent",
    "dismissal_rate_vs_current_opponent",
    "centuries_vs_current_opponent",
    "fifties_vs_current_opponent",

    "runs_vs_australia",
    "average_vs_australia",
    "innings_vs_australia",

    "runs_vs_england",
    "average_vs_england",
    "innings_vs_england",

    "runs_at_venue",
    "innings_at_venue",
    "average_at_venue",
    "strike_rate_at_venue",
    "venue_experience",
    "venue_scoring_difficulty",

    "team_batting_strength",
    "team_recent_form",
    "opponent_bowling_strength",

    "batting_position",
    "venue",
    "venue_country",
    "innings_number",
    "opponent",
    "home_or_away",
]


LEAKAGE_COLUMNS = [
    "Runs",
    "Is_Dismissed",
    "Balls_Faced",
    "Dismissal_Kind",
    "Dismissal_Bowler",
    "Dismissal_Fielders",
    "Match_Result",
    "Winning_Team",
    "Margin",
]


# =========================
# Load
# =========================

df = pd.read_csv(CSV, parse_dates=["Match_Date"])

print(f"Loaded {len(df):,} rows from {CSV}\n")


# Basic validation

chk(
    "Dataset is not empty",
    len(df) > 0
)


missing_features = set(FEATURE_COLUMNS + [TARGET]) - set(df.columns)

chk(
    "All required ML columns exist",
    not missing_features,
    str(missing_features)
)
chk(
    "Old next_innings_runs target removed",
    "next_innings_runs" not in df.columns
)

if missing_features:
    print("\nSchema validation failed")
    sys.exit(1)

actual_feature_columns = [
    c for c in FEATURE_COLUMNS
    if c in df.columns
]
chk(
    "Feature list matches dataset",
    set(FEATURE_COLUMNS).issubset(df.columns),
    str(set(FEATURE_COLUMNS) - set(df.columns))
)

used_dataframe_leaks = [
    c for c in LEAKAGE_COLUMNS
    if c in actual_feature_columns
]

chk(
    "No leakage columns exist in dataframe feature space",
    len(used_dataframe_leaks) == 0,
    str(used_dataframe_leaks)
)


# Duplicate checks

chk(
    "No complete duplicate rows",
    not df.duplicated().any()
)


dup_keys = [
    "Match_ID",
    "Player",
    "Innings_Number"
]


chk(
    "No duplicate Match_ID + Player + Innings_Number",
    not df.duplicated(subset=dup_keys).any()
)

# Target validation

chk(
    "Target has no nulls",
    df[TARGET].notna().all()
)

chk(
    "Target is numeric",
    pd.api.types.is_numeric_dtype(df[TARGET])
)

chk(
    "Target non-negative",
    (df[TARGET] >= 0).all()
)

chk(
    f"Target <= {MAX_PLAUSIBLE_RUNS}",
    (df[TARGET] <= MAX_PLAUSIBLE_RUNS).all()
)


# Leakage validation

used_leaks = [
    c for c in LEAKAGE_COLUMNS
    if c in FEATURE_COLUMNS
]


chk(
    "No leakage columns included as features",
    len(used_leaks) == 0,
    str(used_leaks)
)


# Numeric sanity

numeric_cols = df.select_dtypes(include=np.number).columns

inf_values = {
    c: int(np.isinf(df[c]).sum())
    for c in numeric_cols
    if np.isinf(df[c]).any()
}


chk(
    "No infinite numeric values",
    len(inf_values) == 0,
    str(inf_values)
)


# Career feature validation

# Match_ID included as a tiebreaker to match the row order
# feature_engineering.py actually used when computing these features
# (Match_Date alone doesn't disambiguate innings within the same Test).
ordered = df.sort_values(
    [
        "Player",
        "Match_Date",
        "Match_ID",
        "Innings_Number"
    ]
)


# first innings:

first_player = ordered[
    ordered.groupby("Player").cumcount() == 0
]


chk(
    "First innings career_innings == 0",
    (first_player["career_innings"] == 0).all()
)


chk(
    "First innings career_runs == 0",
    (first_player["career_runs"] == 0).all()
)


for col in [
    "career_innings",
    "career_runs",
    "career_centuries",
    "career_fifties",
]:

    decreases = (
        ordered.groupby("Player")[col]
        .diff()
        .dropna()
        < 0
    ).sum()

    chk(
        f"{col} never decreases",
        decreases == 0,
        f"{decreases} decrease(s)"
    )


# =========================
# Rolling feature validation
# =========================

for col in [
    "last_3_average",
    "last_5_average",
    "last_10_average",
]:

    chk(
        f"First innings {col} is null",
        first_player[col].isna().all()
    )

# Opponent validation

opp_ordered = df.sort_values(
    [
        "Player",
        "Opponent",
        "Match_Date",
        "Match_ID",
        "Innings_Number"
    ]
)


first_vs_opponent = opp_ordered[
    opp_ordered.groupby(
        ["Player", "Opponent"]
    ).cumcount() == 0
]


chk(
    "First innings vs opponent has innings_vs_current_opponent == 0",
    (
        first_vs_opponent["innings_vs_current_opponent"] == 0
    ).all()
)


decreases = (
    opp_ordered
    .groupby(["Player", "Opponent"])
    ["innings_vs_current_opponent"]
    .diff()
    .dropna()
    < 0
).sum()


chk(
    "innings_vs_current_opponent never decreases",
    decreases == 0,
    f"{decreases} decrease(s)"
)


# Opponent feature ranges

NON_NEGATIVE = [
    "runs_vs_current_opponent",
    "innings_vs_current_opponent",
    "average_vs_current_opponent",
    "centuries_vs_current_opponent",
    "fifties_vs_current_opponent",

    "runs_vs_australia",
    "innings_vs_australia",

    "runs_vs_england",
    "innings_vs_england",

    "runs_at_venue",
    "innings_at_venue",
    "venue_experience",
]


for col in NON_NEGATIVE:

    chk(
        f"{col} non-negative",
        (df[col].dropna() >= 0).all()
    )


# Category validation

chk(
    "home_or_away contains only valid values",
    set(df["home_or_away"].dropna().unique())
    <= {"Home", "Away", "Neutral"},
    str(set(df["home_or_away"].dropna().unique()))
)


# Finish

print("\n-------")

if all(checks):
    print(
        f"All {len(checks)} validation checks PASSED"
    )
    sys.exit(0)

else:
    failed = len(checks) - sum(checks)
    print(
        f"{failed} of {len(checks)} validation checks FAILED"
    )
    sys.exit(1)