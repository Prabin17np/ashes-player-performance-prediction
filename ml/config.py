# config.py

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

RAW_DIR = BASE_DIR / "data" / "raw"
OUT_DIR = BASE_DIR / "output"
LOG_DIR = BASE_DIR / "logs"

PARSER_OUTPUT_FILE = OUT_DIR / "batting_dataset.csv"
LOG_FILE = LOG_DIR / "parse_errors.log"
ML_OUTPUT_FILE = OUT_DIR / "final_ml_dataset.csv"

TARGET_COLUMN = "Runs"

START_YEAR = 2010
END_YEAR   = 2026
TARGET_TEAMS = {"England", "Australia"}

RECENT_FORM_WINDOWS = (3, 5, 10)

ROLLING_STRIKE_RATE_WINDOW = 10

TEAM_RECENT_MATCH_WINDOW = 5

SERIES_GAP_THRESHOLD_DAYS = 60

VALID_TOSS_DECISIONS = {
    "bat",
    "field",
}

# Highest individual Test innings ever recorded is 400* (Lara, 2004) —
# anything above this is almost certainly a parsing bug, not real cricket.
MAX_PLAUSIBLE_RUNS = 400
DUPLICATE_KEY_COLUMNS = [
    "Match_ID",
    "Player",
    "Team",
    "Innings_Number",
]

REQUIRED_COLUMNS = {
    "Match_ID",
    "Match_Date",
    "Player",
    "Team",
    "Opponent",
    "Venue",
    "Runs",
    "Balls_Faced",
    "Innings_Number",
    "Batting_Position",
    "Is_Dismissed",
    "Dismissal_Kind",
    "Dismissal_Bowler",
    "Dismissal_Fielders",
    "Toss_Winner",
    "Toss_Decision",
    "Match_Result",
    "Winning_Team",
    "Margin",
}
VALID_TEST_NATIONS = {
    "Afghanistan",
    "Australia",
    "Bangladesh",
    "England",
    "India",
    "Ireland",
    "New Zealand",
    "Pakistan",
    "South Africa",
    "Sri Lanka",
    "West Indies",
    "Zimbabwe",
}