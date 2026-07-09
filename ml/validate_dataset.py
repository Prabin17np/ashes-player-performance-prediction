
import sys
import pandas as pd

from ml.config import (
    START_YEAR,
    END_YEAR,
    TARGET_TEAMS,
    MAX_PLAUSIBLE_RUNS,
    REQUIRED_COLUMNS,
    PARSER_OUTPUT_FILE,
    DUPLICATE_KEY_COLUMNS,
    VALID_TOSS_DECISIONS,
    VALID_TEST_NATIONS,
)

CSV = str(PARSER_OUTPUT_FILE)

checks = []


def chk(label, result, detail=""):
    status = "✓" if result else "✗ FAIL"
    print(f"[{status}] {label}" + (f" -> {detail}" if detail else ""))
    checks.append(result)

# Load Dataset


df = pd.read_csv(CSV, parse_dates=["Match_Date"])

print(f"Loaded {len(df):,} rows from {CSV}\n")


# Schema Validation

missing_cols = REQUIRED_COLUMNS - set(df.columns)

chk(
    "Required columns present",
    not missing_cols,
    str(missing_cols) if missing_cols else "",
)

if missing_cols:
    print("\nSchema validation failed. Aborting.")
    sys.exit(1)


# Basic Dataset Checks

chk("Dataset is not empty", len(df) > 0)

chk(
    "Teams only England/Australia",
    set(df["Team"].unique()) <= TARGET_TEAMS,
    str(set(df["Team"].unique())),
)

chk(
    "Years within configured range",
    df["Match_Date"].dt.year.between(START_YEAR, END_YEAR).all(),
)

chk(
    "Runs >= 0",
    (df["Runs"] >= 0).all(),
)

chk(
    f"Runs <= {MAX_PLAUSIBLE_RUNS}",
    (df["Runs"] <= MAX_PLAUSIBLE_RUNS).all(),
    f"{(df['Runs'] > MAX_PLAUSIBLE_RUNS).sum()} violation(s)",
)

valid_balls = df["Balls_Faced"].dropna()

chk(
    "Balls_Faced >= 0",
    (valid_balls >= 0).all(),
)

with_balls = df.dropna(subset=["Balls_Faced"])

over_cap = with_balls[
    with_balls["Runs"] > with_balls["Balls_Faced"] * 6
]

chk(
    "Runs <= Balls_Faced * 6",
    len(over_cap) == 0,
    f"{len(over_cap)} violation(s)",
)

chk(
    "Team != Opponent",
    (df["Team"] != df["Opponent"]).all(),
)


chk(
    "Opponents are valid Test nations",
    set(df["Opponent"].dropna().unique()) <= VALID_TEST_NATIONS,
    str(sorted(df["Opponent"].dropna().unique())),
)
chk(
    "Contains multiple opponents",
    df["Opponent"].nunique() > 2,
    f"{df['Opponent'].nunique()} opponents found",
)

chk(
    "Contains England vs Australia matches",
    (
        ((df["Team"] == "England") & (df["Opponent"] == "Australia"))
        |
        ((df["Team"] == "Australia") & (df["Opponent"] == "England"))
    ).any(),
)

chk(
    "Innings_Number between 1 and 4",
    df["Innings_Number"].between(1, 4).all(),
)

# Match_ID Checks

chk(
    "No null Match_ID",
    df["Match_ID"].notna().all(),
)

chk(
    "Each Match_ID maps to one Match_Date",
    df.groupby("Match_ID")["Match_Date"].nunique().eq(1).all(),
)

valid_positions = df["Batting_Position"].dropna()

chk(
    "Batting_Position between 1 and 11",
    valid_positions.between(1, 11).all(),
    f"{(~valid_positions.between(1, 11)).sum()} violation(s)",
)

dup_bp = df.duplicated(
    subset=[
        "Match_ID",
        "Team",
        "Innings_Number",
        "Batting_Position",
    ]
)

chk(
    "No duplicate Batting_Position in an innings",
    not dup_bp.any(),
    f"{dup_bp.sum()} duplicate(s)",
)

# Contiguous batting order

contiguous = True

for (_, _, _), group in df.groupby(
    ["Match_ID", "Team", "Innings_Number"]
):

    positions = sorted(
        group["Batting_Position"]
        .dropna()
        .astype(int)
        .tolist()
    )

    expected = list(range(1, len(positions) + 1))

    if positions != expected:
        contiguous = False
        break

chk(
    "Batting positions are contiguous",
    contiguous,
)

# Toss Checks


chk(
    "No null Toss_Winner",
    df["Toss_Winner"].notna().all(),
)

chk(
    "Valid Toss_Decision",
    df["Toss_Decision"].isin(VALID_TOSS_DECISIONS).all(),
)

# Null Checks

for col in [
    "Match_Date",
    "Player",
    "Team",
    "Opponent",
    "Venue",
    "Match_Result",
]:
    chk(
        f"No null {col}",
        df[col].notna().all(),
    )

# Margin and Winning_Team may legitimately be null (draw/tie/no result)

# Duplicate Innings


chk(
    "No duplicate innings rows",
    ~df.duplicated(subset=DUPLICATE_KEY_COLUMNS).any(),
)

print("\nDataset Coverage")
print("----------------")
print(f"Players      : {df['Player'].nunique():,}")
print(f"Matches      : {df['Match_ID'].nunique():,}")
print(f"Teams        : {sorted(df['Team'].unique())}")
print(f"Opponents    : {sorted(df['Opponent'].unique())}")
print(f"Venues       : {df['Venue'].nunique():,}")

if all(checks):
    print("All validation checks PASSED ✓")
    sys.exit(0)
else:
    print("Some validation checks FAILED ✗")
    sys.exit(1)