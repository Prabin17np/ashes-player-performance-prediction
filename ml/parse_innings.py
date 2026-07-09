
import json
import logging
from pathlib import Path
from datetime import datetime, date

import pandas as pd

from ml.config import (
    RAW_DIR, PARSER_OUTPUT_FILE, LOG_DIR, LOG_FILE,
    START_YEAR, END_YEAR, TARGET_TEAMS, MAX_PLAUSIBLE_RUNS, REQUIRED_COLUMNS,
    DUPLICATE_KEY_COLUMNS, VALID_TOSS_DECISIONS,
)

# Logging

LOG_DIR.mkdir(parents=True, exist_ok=True)
PARSER_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="w"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

# Step 1: File Discovery

def discover_files(raw_dir: Path) -> list[Path]:
    files = sorted(raw_dir.rglob("*.json"))
    log.info(f"Discovered {len(files)} JSON file(s) in '{raw_dir}'")
    if not files:
        raise FileNotFoundError(
            f"No JSON files found in '{raw_dir}'. "
            "Download Test files from https://cricsheet.org/downloads/ and unzip into data/raw/"
        )
    return files


# Step 2: Date Parsing

def parse_match_date(info: dict) -> date | None:
    raw_dates = info.get("dates", [])
    if not raw_dates:
        return None
    first = raw_dates[0]
    if isinstance(first, date):
        return first
    try:
        return datetime.strptime(str(first), "%Y-%m-%d").date()
    except ValueError:
        return None


# Step 3: Match-Level Filtering (kept separate from extraction)

def match_passes_filters(info: dict, match_date: date | None, filepath: Path) -> bool:
    """
    Business-rule filtering only: match type, date range, team involvement.
    Deliberately kept out of the extraction function so extraction can be
    unit-tested independently of filtering rules.
    """
    if info.get("match_type", "").lower() != "test":
        return False

    if match_date is None:
        log.warning(f"  No valid date in {filepath.name} — skipping")
        return False
    if not (START_YEAR <= match_date.year <= END_YEAR):
        return False

    # Any match involving EITHER target team qualifies (not just Ashes).
    teams = set(info.get("teams", []))
    if not (teams & TARGET_TEAMS):
        return False

    return True


# Step 4: Schema-Version-Safe Field Access

def get_batter(delivery: dict) -> str:
    """Cricsheet renamed 'batsman' -> 'batter' at some point. Support both."""
    return delivery.get("batter") or delivery.get("batsman") or ""


def get_non_striker(delivery: dict) -> str:
    return delivery.get("non_striker", "")


def get_batter_runs(runs_block: dict) -> int:
    if "batter" in runs_block:
        return runs_block.get("batter", 0)
    return runs_block.get("batsman", 0)


def get_venue(info: dict, filepath: Path) -> str | None:
    venue = info.get("venue")
    if not venue:
        log.warning(f"  No venue recorded in {filepath.name}")
        return None
    return venue


# Step 4b: Match-Level Metadata (toss & result)

def get_toss_info(info: dict) -> tuple[str | None, str | None]:
    toss = info.get("toss", {}) or {}
    return toss.get("winner"), toss.get("decision")


def get_match_outcome(info: dict) -> tuple[str, str | None, str | None]:
    """
    Returns (Match_Result, Winning_Team, Margin).

    Cricsheet 'outcome' shapes seen in practice:
      {"winner": "England", "by": {"runs": 45}}                -> win, "45 runs"
      {"winner": "England", "by": {"innings": 1, "runs": 45}}  -> win, "innings and 45 runs"
      {"winner": "England", "by": {"wickets": 5}}               -> win, "5 wickets"
      {"result": "draw"} / {"result": "tie"} / {"result": "no result"}
    """
    outcome = info.get("outcome", {}) or {}

    if "winner" in outcome:
        winner = outcome["winner"]
        by = outcome.get("by", {}) or {}
        if "runs" in by:
            margin = f"innings and {by['runs']} runs" if "innings" in by else f"{by['runs']} runs"
        elif "wickets" in by:
            margin = f"{by['wickets']} wickets"
        else:
            margin = None
        return "win", winner, margin

    # No winner recorded -> draw / tie / no result
    result = outcome.get("result", "draw")
    return result, None, None


# Step 5: Player–Team Registry

def build_player_team_map(info: dict) -> dict[str, str]:
    registry: dict[str, str] = {}
    for team, players in info.get("players", {}).items():
        for player in players:
            registry[player] = team
    return registry


# Step 6: Innings Extraction (pure structural extraction, no filtering)

def extract_innings_records(match: dict, match_date: date, venue: str | None, match_id: str) -> list[dict]:
    info    = match.get("info", {})
    innings = match.get("innings", [])
    teams_in_match = info.get("teams", [])

    # Match-level metadata (constant across all innings/records of this
    # match) — computed once here rather than per-innings or per-delivery.
    toss_winner, toss_decision = get_toss_info(info)
    match_result, winning_team, margin = get_match_outcome(info)

    records: list[dict] = []

    for innings_idx, innings_block in enumerate(innings):
        batting_team = innings_block.get("team", "")
        innings_num  = innings_idx + 1

        if batting_team not in TARGET_TEAMS:
            continue

        opponent = next((t for t in teams_in_match if t != batting_team), "Unknown")

        batter_runs:       dict[str, int]  = {}
        batter_balls:      dict[str, int]  = {}
        batter_dismissals: dict[str, dict] = {}
        batting_order:     dict[str, int]  = {}  # first-appearance order -> position (1-based)

        def _register_batting_position(name: str) -> None:
        
            if name and name not in batting_order:
                batting_order[name] = len(batting_order) + 1

        for over_block in innings_block.get("overs", []):
            for delivery in over_block.get("deliveries", []):
                batter = get_batter(delivery)
                if not batter:
                    continue

                _register_batting_position(batter)
                _register_batting_position(get_non_striker(delivery))

                runs_block = delivery.get("runs", {})
                batter_runs_this_ball = get_batter_runs(runs_block)

                extras  = delivery.get("extras", {}) or {}
                is_wide = "wides" in extras

                batter_runs[batter] = batter_runs.get(batter, 0) + batter_runs_this_ball
                if not is_wide:
                    batter_balls[batter] = batter_balls.get(batter, 0) + 1

                for wicket in (delivery.get("wickets", []) or []):
                    player_out = wicket.get("player_out", "")
                    if not player_out:
                        continue
                    kind = wicket.get("kind")

                    fielder_names = []
                    for f in (wicket.get("fielders", []) or []):
                        name = f.get("name") if isinstance(f, dict) else f
                        if name:
                            fielder_names.append(name)

                    # No bowler is credited for a run out.
                    dismissal_bowler = (
                        delivery.get("bowler")
                        if kind and kind.lower() != "run out"
                        else None
                    )

                    batter_dismissals[player_out] = {
                        "kind":     kind,
                        "bowler":   dismissal_bowler,
                        "fielders": ", ".join(fielder_names) if fielder_names else None,
                    }

        # Emit one record per batter who was ever assigned a batting
        for batter in batting_order:
            runs = batter_runs.get(batter, 0)
            dismissal = batter_dismissals.get(batter)
            records.append({
                "Match_ID":           match_id,
                "Match_Date":         match_date.isoformat(),
                "Player":             batter,
                "Team":               batting_team,  # already scoped to this innings — no lookup needed
                "Opponent":           opponent,
                "Venue":              venue,
                "Toss_Winner":        toss_winner,
                "Toss_Decision":      toss_decision,
                "Match_Result":       match_result,
                "Winning_Team":       winning_team,
                "Margin":             margin,
                "Runs":               runs,
                "Balls_Faced":        batter_balls.get(batter, None),
                "Innings_Number":     innings_num,
                "Batting_Position":   batting_order.get(batter),
                "Is_Dismissed":       dismissal is not None,
                "Dismissal_Kind":     dismissal["kind"]     if dismissal else None,
                "Dismissal_Bowler":   dismissal["bowler"]   if dismissal else None,
                "Dismissal_Fielders": dismissal["fielders"] if dismissal else None,
            })

    return records


# Step 7: Single-File Parser (thin orchestration wrapper)

def parse_file(filepath: Path, raw_dir: Path) -> list[dict]:
    with open(filepath, encoding="utf-8") as f:
        match = json.load(f)

    info       = match.get("info", {})
    match_date = parse_match_date(info)

    if not match_passes_filters(info, match_date, filepath):
        return []

    venue = get_venue(info, filepath)

    match_id = filepath.relative_to(raw_dir).as_posix()

    return extract_innings_records(match, match_date, venue, match_id)


# Step 8: Orchestrator

def build_dataset(raw_dir: Path) -> pd.DataFrame:
    files = discover_files(raw_dir)
    all_records: list[dict] = []
    skipped = 0
    parsed  = 0

    for filepath in files:
        try:
            records = parse_file(filepath, raw_dir)
            all_records.extend(records)
            if records:
                parsed += 1
        except Exception as exc:
            # Broadened from (JSONDecodeError, KeyError, TypeError) — any
            # unexpected shape shouldn't crash the whole batch run.
            log.error(f"  PARSE ERROR in {filepath.name}: {type(exc).__name__}: {exc}")
            skipped += 1

    log.info(f"Parsed {parsed} qualifying file(s); skipped {skipped} file(s) with errors")
    log.info(f"Raw records collected: {len(all_records)}")

    if not all_records:
        log.warning("No records matched the filters. Check your JSON files and date range.")
        return pd.DataFrame()

    return pd.DataFrame(all_records)


# Step 9: Cleaning & Type Enforcement

def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df["Match_Date"]     = pd.to_datetime(df["Match_Date"])

    # Don't silently zero-fill unparseable Runs — that masks real parsing
    # bugs as legitimate ducks. Drop and log instead.
    runs_numeric = pd.to_numeric(df["Runs"], errors="coerce")
    invalid_mask = runs_numeric.isna()
    if invalid_mask.any():
        log.warning(f"Dropping {invalid_mask.sum()} row(s) with unparseable Runs values")
        df = df.loc[~invalid_mask].copy()
        runs_numeric = runs_numeric.loc[~invalid_mask]
    df["Runs"] = runs_numeric.astype(int)

    df["Balls_Faced"]      = pd.to_numeric(df["Balls_Faced"], errors="coerce")  # keep NaN where unavailable
    df["Innings_Number"]   = pd.to_numeric(df["Innings_Number"], errors="coerce").astype(int)

    df["Batting_Position"] = pd.to_numeric(df["Batting_Position"], errors="coerce")

    string_cols = [
        "Player", "Team", "Opponent", "Venue", "Dismissal_Kind", "Dismissal_Bowler", "Dismissal_Fielders",
        # New string-typed metadata columns — stripped the same way as the
        # existing ones so downstream comparisons/groupbys aren't broken by
        # stray whitespace from source JSON.
        "Match_ID", "Toss_Winner", "Toss_Decision",
        "Match_Result", "Winning_Team", "Margin",
    ]
    for col in string_cols:
        df[col] = df[col].str.strip()


    before = len(df)
    df.drop_duplicates(
        subset=DUPLICATE_KEY_COLUMNS,
        keep="first",
        inplace=True,
    )
    dupes_removed = before - len(df)
    if dupes_removed:
        log.warning(f"Removed {dupes_removed} duplicate row(s)")

    df.sort_values(["Match_Date", "Innings_Number", "Team", "Player"], inplace=True)
    df.reset_index(drop=True, inplace=True)

    return df


# Step 10: Data Validation

def validate(df: pd.DataFrame) -> bool:
    log.info("-- Validation Checks --")
    passed = True

    def check(condition: bool, msg_ok: str, msg_fail: str):
        nonlocal passed
        if condition:
            log.info(f"  ✓  {msg_ok}")
        else:
            log.warning(f"  ✗  FAIL: {msg_fail}")
            passed = False

    check(len(df) > 0, f"Non-empty dataset ({len(df)} rows)", "Dataset is empty!")

    check(REQUIRED_COLUMNS.issubset(df.columns),
          "All required columns present",
          f"Missing columns: {REQUIRED_COLUMNS - set(df.columns)}")

    unexpected_teams = set(df["Team"].unique()) - TARGET_TEAMS
    check(not unexpected_teams,
          "All Team values are England or Australia",
          f"Unexpected teams found: {unexpected_teams}")

    years = df["Match_Date"].dt.year
    check(years.min() >= START_YEAR and years.max() <= END_YEAR,
          f"All dates within {START_YEAR}–{END_YEAR}",
          f"Dates out of range: min={years.min()}, max={years.max()}")

    check((df["Runs"] >= 0).all(),
          "No negative Runs values",
          f"{(df['Runs'] < 0).sum()} rows have negative Runs")

    check((df["Runs"] <= MAX_PLAUSIBLE_RUNS).all(),
          f"No implausible Runs values (<= {MAX_PLAUSIBLE_RUNS})",
          f"{(df['Runs'] > MAX_PLAUSIBLE_RUNS).sum()} row(s) exceed {MAX_PLAUSIBLE_RUNS} runs")

    valid_balls = df["Balls_Faced"].dropna()
    check((valid_balls >= 0).all(),
          "No negative Balls_Faced values",
          f"{(valid_balls < 0).sum()} rows have negative Balls_Faced")

    with_balls = df.dropna(subset=["Balls_Faced"])
    over_cap = with_balls[with_balls["Runs"] > with_balls["Balls_Faced"] * 6]
    check(len(over_cap) == 0,
          "Runs never exceed Balls_Faced * 6",
          f"{len(over_cap)} row(s) violate the max-runs-per-ball constraint")

    check((df["Team"] != df["Opponent"]).all(),
          "Team never equals Opponent",
          f"{(df['Team'] == df['Opponent']).sum()} row(s) have Team == Opponent")

    check(df["Innings_Number"].between(1, 4).all(),
          "Innings_Number always between 1 and 4",
          f"Unexpected innings numbers: {df.loc[~df['Innings_Number'].between(1,4), 'Innings_Number'].unique()}")

    # Match_ID uniqueness: not "unique per row" (many batting records share
    # a Match_ID by design), but "unique per match" — i.e. a given Match_ID
    # never maps to more than one underlying (Match_Date, Venue) pair.
    match_id_groups = df.groupby("Match_ID")[["Match_Date", "Venue"]].nunique()
    inconsistent_ids = match_id_groups[(match_id_groups["Match_Date"] > 1) | (match_id_groups["Venue"] > 1)]
    check(len(inconsistent_ids) == 0,
          "Every Match_ID maps to exactly one match",
          f"{len(inconsistent_ids)} Match_ID(s) map to more than one Match_Date/Venue")

    # Batting_Position is intentionally nullable (see clean_dataframe) —
    # only the range of non-null values is checked, never "must be present".
    valid_positions = df["Batting_Position"].dropna()
    check(valid_positions.between(1, 11).all(),
          "Batting_Position always between 1 and 11",
          f"{(~valid_positions.between(1, 11)).sum()} row(s) have an out-of-range Batting_Position")

    dup_positions = df.dropna(subset=["Batting_Position"]).duplicated(
        subset=["Match_ID", "Innings_Number", "Team", "Batting_Position"]
    )
    check(not dup_positions.any(),
          "No duplicate Batting_Position within the same innings",
          f"{dup_positions.sum()} duplicate Batting_Position row(s) found")

    # Uses VALID_TOSS_DECISIONS from config.py instead of a locally
    # hardcoded {"bat", "field"} literal. Also actually checks Toss_Winner
    # for nulls now (Rev 3 fixed this — previously the condition only
    # tested Toss_Decision despite the message claiming to check both).
    toss_decisions_present = set(df["Toss_Decision"].dropna().unique())
    check(
        toss_decisions_present.issubset(VALID_TOSS_DECISIONS)
        and df["Toss_Decision"].notna().all()
        and df["Toss_Winner"].notna().all(),
        "Toss_Winner/Toss_Decision present and valid for every row",
        f"Missing Toss_Winner: {df['Toss_Winner'].isna().sum()}, "
        f"unexpected Toss_Decision values: {toss_decisions_present - VALID_TOSS_DECISIONS}",
    )
    # -------------------------------------------------------------------------

    for col in ["Match_ID", "Match_Date", "Player", "Team", "Innings_Number", "Opponent", "Venue"]:
        nulls = df[col].isna().sum()
        check(nulls == 0, f"No nulls in '{col}'", f"{nulls} null(s) in '{col}'")

    log.info("------------------------------")
    return passed

# Step 11: Summary Statistics
def print_summary(df: pd.DataFrame):
    log.info("------------ Dataset Summary --------------")
    log.info(f"  Total rows         : {len(df):,}")
    log.info(f"  Unique players     : {df['Player'].nunique():,}")
    log.info(f"  Unique matches     : {df['Match_ID'].nunique():,}")
    log.info(f"  Date range         : {df['Match_Date'].min().date()} → {df['Match_Date'].max().date()}")
    log.info(f"  Balls_Faced NaN%   : {df['Balls_Faced'].isna().mean():.1%}")
    log.info(f"  Dismissal rate     : {df['Is_Dismissed'].mean():.1%}")
    log.info(f"  Rows per team:\n{df['Team'].value_counts().to_string()}")

    # 2 — England/Australia coverage summary
    eng_df = df[df["Team"] == "England"]
    aus_df = df[df["Team"] == "Australia"]
    log.info("  -- England/Australia coverage --")
    log.info(f"  Total matches processed        : {df['Match_ID'].nunique():,}")
    log.info(f"  Matches containing England      : {eng_df['Match_ID'].nunique():,}")
    log.info(f"  Matches containing Australia     : {aus_df['Match_ID'].nunique():,}")
    log.info(f"  England batting innings rows     : {len(eng_df):,}")
    log.info(f"  Australia batting innings rows   : {len(aus_df):,}")
    log.info(f"  Unique opponents included        : {sorted(df['Opponent'].unique())}")

    log.info(f"  Top 5 run-scorers (career total):")
    top = df.groupby("Player")["Runs"].sum().nlargest(5)
    for player, runs in top.items():
        log.info(f"    {player:<30} {runs:>5} runs")
    log.info("------------------------------------------")


def main():
    log.info("Starting Cricket Batting Dataset Builder")
    # 1
    log.info(f"Filter: England/Australia player innings from all Test matches | Years: {START_YEAR}–{END_YEAR}")

    df = build_dataset(RAW_DIR)

    if df.empty:
        log.error("Aborting: no data to save.")
        return

    df = clean_dataframe(df)
    is_valid = validate(df)

    df.to_csv(PARSER_OUTPUT_FILE, index=False)
    log.info(f"Saved → {PARSER_OUTPUT_FILE}  ({len(df):,} rows)")

    print_summary(df)



    if not is_valid:
        log.warning("Validation had failures — review logs before using dataset.")


if __name__ == "__main__":
    main()