"""
eda.py

Exploratory Data Analysis for the engineered Ashes batting-performance
dataset (config.ML_OUTPUT_FILE).
implementation.

Structure
Part 1   dataset_overview               -- shape, dtypes, memory, coverage basics
Part 2   validate_feature_columns       -- FEATURE_COLUMNS presence/duplicates
Part 3   missing_value_analysis         -- expected (history) vs. unexpected nulls
Part 4   target_variable_analysis       -- histogram+KDE, boxplot, moments
Part 5   plot_numerical_distributions   -- one histogram per numeric feature
Part 6   correlation_analysis           -- Pearson heatmap + ranked table
Part 7   mutual_information_analysis    -- MI over ALL of FEATURE_COLUMNS
Part 8   categorical_analysis           -- mean/median Runs per category
Part 9   detect_outliers                -- IQR + Z-score counts (report only)
Part 10  multicollinearity_vif          -- VIF over numeric FEATURE_COLUMNS
Part 11  validate_feature_engineering   -- leakage-safety re-verification
Part 12  validate_no_leakage            -- hard-fail check vs. train_model gate
Part 13  dataset_coverage               -- matches/players per year, distributions
Part 14  feature_readiness_report       -- consolidated thesis-ready summary
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd
from scipy import stats
import matplotlib
matplotlib.use("Agg")  # headless-safe backend; script only writes files
import matplotlib.pyplot as plt

from sklearn.feature_selection import mutual_info_regression
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression

from ml.config import ML_OUTPUT_FILE, OUT_DIR

# feature_engineering.py is the single source of truth for the model's
# feature set and for the leakage-safe engineering design (which columns
# are cumulative career features, which are pure match context, how the
# dataset is chronologically ordered, etc).
from ml.feature_engineering import (
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    CAREER_FEATURES,
    RECENT_FORM_FEATURES,
    MATCH_CONTEXT_FEATURES,
    ID_COLUMNS,
    SORT_COLUMNS,
)

# train_model.py owns the actual pre-training leakage gate. Importing its
# constants (rather than re-declaring them) guarantees Part 12 below tests
# against the same list train_model.validate_before_training() enforces.
# NOTE: this import also triggers train_model.py's optional xgboost/catboost
# imports (guarded there with try/except) -- harmless, no code executes
# beyond module-level definitions since train_model.py guards main() behind
# `if __name__ == "__main__"`.
from ml.train_model import (
    LEAKAGE_COLUMNS,
    OLD_TARGET_COLUMN,
    DATE_COLUMN,
)
# Raw identifier columns
# NOT part of FEATURE_COLUMNS -- these are structural dataset columns used
# only for descriptive/coverage reporting (Parts 1 and 13), never as model
# inputs. Referenced by literal name because they are base dataset schema
# columns that already appear by these same names inside
# feature_engineering.py (ID_COLUMNS, SORT_COLUMNS, REQUIRED_INPUT_COLUMNS).

RAW_PLAYER_COLUMN = "Player"
RAW_TEAM_COLUMN = "Team"
RAW_OPPONENT_COLUMN = "Opponent"
RAW_VENUE_COLUMN = "Venue"
RAW_MATCH_ID_COLUMN = "Match_ID"

# Runs bucket, used consistently with train_model.py's evaluation scheme so
# the descriptive EDA and the trained-model evaluation talk about the same
# regimes of the target variable.
RUNS_BUCKET_EDGES = (0, 10, 50, 1000)
RUNS_BUCKET_LABELS = ("0-10", "11-50", "51+")

# Output locations

EDA_DIR = OUT_DIR / "eda"
FIG_DIR = EDA_DIR / "figures"
DIST_DIR = FIG_DIR / "distributions"
CAT_DIR = FIG_DIR / "categorical"
COVERAGE_DIR = EDA_DIR / "coverage"


def ensure_output_dirs() -> None:
    """Create every output directory this script writes to, if missing."""
    for directory in (EDA_DIR, FIG_DIR, DIST_DIR, CAT_DIR, COVERAGE_DIR):
        directory.mkdir(parents=True, exist_ok=True)

# Helpers

def _save_fig(fig: plt.Figure, path: Path) -> None:
    """Save a figure to disk and close it (keeps memory bounded across
    the many plots this script produces)."""
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def load_dataset(path: Path = ML_OUTPUT_FILE) -> pd.DataFrame:
    """Load the engineered dataset for analysis only."""
    if not path.exists():
        raise FileNotFoundError(
            f"Engineered dataset not found at '{path}'. Run feature_engineering.py first."
        )
    df = pd.read_csv(path)
    df[DATE_COLUMN] = pd.to_datetime(df[DATE_COLUMN])
    return df


def classify_feature_types(
    df: pd.DataFrame, feature_columns: list[str] = FEATURE_COLUMNS
) -> tuple[list[str], list[str], list[str]]:
    """Determine numeric / categorical / boolean feature types from actual
    dataframe dtypes, restricted to FEATURE_COLUMNS.
    """
    boolean_cols = [c for c in feature_columns if pd.api.types.is_bool_dtype(df[c])]
    numeric_cols = [
        c for c in feature_columns
        if pd.api.types.is_numeric_dtype(df[c]) and c not in boolean_cols
    ]
    categorical_cols = [
        c for c in feature_columns if c not in boolean_cols and c not in numeric_cols
    ]
    return numeric_cols, categorical_cols, boolean_cols

# Part 1 -- Dataset Overview

def dataset_overview(df: pd.DataFrame) -> pd.DataFrame:

    """
    Report shape, dtypes, memory usage, date range, and basic coverage
    counts (unique players / venues / opponents / matches).
    Returns
    pd.DataFrame with one row per column (saved as dataset_summary.csv).
    """
    
    print("=" * 70)
    print("PART 1 -- DATASET OVERVIEW")
    print("=" * 70)

    n_rows, n_cols = df.shape
    total_memory_mb = df.memory_usage(deep=True).sum() / (1024 ** 2)

    print(f"Rows                 : {n_rows:,}")
    print(f"Columns              : {n_cols}")
    print(f"Total memory usage   : {total_memory_mb:.2f} MB")
    print(f"Date range           : {df[DATE_COLUMN].min().date()} -> {df[DATE_COLUMN].max().date()}")
    print(f"Unique players       : {df[RAW_PLAYER_COLUMN].nunique():,}")
    print(f"Unique venues        : {df[RAW_VENUE_COLUMN].nunique():,}")
    print(f"Unique opponents     : {df[RAW_OPPONENT_COLUMN].nunique():,}")
    print(f"Unique matches       : {df[RAW_MATCH_ID_COLUMN].nunique():,}")

    summary = pd.DataFrame({
        "column": df.columns,
        "dtype": [str(dt) for dt in df.dtypes],
        "non_null_count": df.notna().sum().to_numpy(),
        "null_count": df.isna().sum().to_numpy(),
        "memory_bytes": df.memory_usage(deep=True, index=False).to_numpy(),
    })
    print("\nPer-column summary:")
    print(summary.to_string(index=False))
    print()
    return summary

# Part 2 -- Feature Validation

def validate_feature_columns(df: pd.DataFrame) -> dict[str, Any]:

    """
    Validate that FEATURE_COLUMNS (imported from feature_engineering.py) is
    usable exactly as-is against dataset.
    """

    print("=" * 70)
    print("PART 2 -- FEATURE VALIDATION")
    print("=" * 70)

    failures: list[str] = []

    duplicate_features = [c for c in set(FEATURE_COLUMNS) if FEATURE_COLUMNS.count(c) > 1]
    if duplicate_features:
        failures.append(f"FEATURE_COLUMNS contains duplicate name(s): {duplicate_features}")

    missing_features = [c for c in FEATURE_COLUMNS if c not in df.columns]
    if missing_features:
        failures.append(f"FEATURE_COLUMNS entries missing from dataset: {missing_features}")

    if failures:
        message = "Feature validation FAILED:\n  - " + "\n  - ".join(failures)
        raise RuntimeError(message)

    known_other = set(
        ID_COLUMNS
        + [RAW_VENUE_COLUMN, TARGET_COLUMN, OLD_TARGET_COLUMN]
        + LEAKAGE_COLUMNS
    )
    unrecognised_columns = [
        c for c in df.columns if c not in FEATURE_COLUMNS and c not in known_other
    ]

    print(f"FEATURE_COLUMNS count       : {len(FEATURE_COLUMNS)}")
    print("All FEATURE_COLUMNS present : yes")
    print("Duplicate feature names     : none")
    if unrecognised_columns:
        print(f"\nColumns present in the dataset but outside all recognised "
              f"categories (feature / target / identifier / leakage): "
              f"{unrecognised_columns}")
        print("(Informational only -- these are not used as model inputs.)")
    else:
        print("\nEvery dataset column is accounted for as a feature, the "
              "target, a raw identifier, or a known leakage/old-target column.")
    print()

    return {
        "feature_count": len(FEATURE_COLUMNS),
        "missing_features": missing_features,
        "duplicate_features": duplicate_features,
        "unrecognised_columns": unrecognised_columns,
    }

# Part 3 -- Missing Value Analysis

def missing_value_analysis(df: pd.DataFrame) -> pd.DataFrame:
  
    print("=" * 70)
    print("PART 3 -- MISSING VALUE ANALYSIS")
    print("=" * 70)

    columns_to_check = FEATURE_COLUMNS + [TARGET_COLUMN]
    missing_count = df[columns_to_check].isna().sum()
    missing_pct = (missing_count / len(df) * 100).round(2)
    report = pd.DataFrame({
        "column": columns_to_check,
        "missing_count": missing_count.to_numpy(),
        "missing_pct": missing_pct.to_numpy(),
    }).sort_values("missing_pct", ascending=False).reset_index(drop=True)

    print(report[report["missing_count"] > 0].to_string(index=False))

    # History-dependent = every feature EXCEPT the static match-context
    # group (venue, opponent, batting position, etc., which are always
    # known ahead of the innings and never null for history reasons).
    history_dependent_cols = [c for c in FEATURE_COLUMNS if c not in MATCH_CONTEXT_FEATURES]

    expected_missing = [
        c for c in history_dependent_cols if c in df.columns and df[c].isna().any()
    ]
    unexpected_missing = [
        c for c in report.loc[report["missing_count"] > 0, "column"]
        if c not in history_dependent_cols
    ]

    print("\nExpected nulls (insufficient prior history -- leakage-safe by design):")
    if expected_missing:
        for col in expected_missing:
            print(f"  - {col}: null until the relevant player/team/venue/opponent "
                  f"has at least one prior qualifying innings.")
    else:
        print("  (none)")

    if unexpected_missing:
        print("\nNulls NOT explained by insufficient history (worth investigating):")
        for col in unexpected_missing:
            print(f"  - {col}")
    else:
        print("\nNo unexplained nulls outside the history-dependent feature set.")

    plot_cols = report.loc[report["missing_count"] > 0]
    if not plot_cols.empty:
        fig, ax = plt.subplots(figsize=(10, max(4, 0.3 * len(plot_cols))))
        ax.barh(plot_cols["column"], plot_cols["missing_pct"], color="steelblue")
        ax.set_xlabel("Missing (%)")
        ax.set_title("Missing Values by Column (FEATURE_COLUMNS + Target)")
        ax.invert_yaxis()
        _save_fig(fig, FIG_DIR / "missing_values.png")
    else:
        print("\nNo missing values at all -- skipping missing-values plot.")

    print()
    return report



# Part 4 -- Target Variable Analysis

def target_variable_analysis(df: pd.DataFrame, target_col: str = TARGET_COLUMN) -> dict[str, float]:
  
    print("=" * 70)
    print(f"PART 4 -- TARGET VARIABLE ('{target_col}')")
    print("=" * 70)

    values = df[target_col].dropna()

    stats_dict = {
        "count": int(values.count()),
        "mean": float(values.mean()),
        "median": float(values.median()),
        "std": float(values.std()),
        "min": float(values.min()),
        "max": float(values.max()),
        "skewness": float(stats.skew(values)),
        "kurtosis": float(stats.kurtosis(values)),  # Fisher (excess) kurtosis
    }
    for key, val in stats_dict.items():
        print(f"{key:>10}: {val:,.3f}" if isinstance(val, float) else f"{key:>10}: {val}")

    # Histogram + KDE
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(values, bins=40, density=True, alpha=0.6, color="steelblue", label="Histogram")
    kde = stats.gaussian_kde(values)
    x_grid = np.linspace(values.min(), values.max(), 400)
    ax.plot(x_grid, kde(x_grid), color="firebrick", linewidth=2, label="KDE")
    ax.set_xlabel(target_col)
    ax.set_ylabel("Density")
    ax.set_title(f"Distribution of {target_col}")
    ax.legend()
    _save_fig(fig, FIG_DIR / "target_distribution.png")

    # Boxplot
    fig, ax = plt.subplots(figsize=(4, 6))
    ax.boxplot(values, vert=True, patch_artist=True,
               boxprops=dict(facecolor="steelblue", alpha=0.6))
    ax.set_ylabel(target_col)
    ax.set_title(f"Boxplot of {target_col}")
    _save_fig(fig, FIG_DIR / "target_boxplot.png")

    print()
    return stats_dict

# Part 5 -- Numerical Feature Distributions

def plot_numerical_distributions(df: pd.DataFrame, numeric_cols: list[str]) -> None:
  
    print("=" * 70)
    print("PART 5 -- NUMERICAL FEATURE DISTRIBUTIONS")
    print("=" * 70)

    for col in numeric_cols:
        values = df[col].dropna()
        if values.empty:
            print(f"  Skipping '{col}': no non-null values.")
            continue
        fig, ax = plt.subplots(figsize=(7, 4.5))
        ax.hist(values, bins=40, color="steelblue", alpha=0.75)
        ax.set_title(f"Distribution of {col}")
        ax.set_xlabel(col)
        ax.set_ylabel("Frequency")
        _save_fig(fig, DIST_DIR / f"{col}.png")

    print(f"Saved {len(numeric_cols)} distribution plot(s) to '{DIST_DIR}'\n")

# Part 6 -- Correlation Analysis

def correlation_analysis(
    df: pd.DataFrame,
    numeric_cols: list[str],
    boolean_cols: list[str],
    target_col: str = TARGET_COLUMN,
) -> tuple[pd.DataFrame, pd.Series]:
   
    print("=" * 70)
    print("PART 6 -- CORRELATION ANALYSIS")
    print("=" * 70)

    corr_cols = numeric_cols + boolean_cols + [target_col]
    corr_df = df[corr_cols].copy()
    for col in boolean_cols:
        corr_df[col] = corr_df[col].astype(int)

    corr_matrix = corr_df.corr(method="pearson")

    fig, ax = plt.subplots(figsize=(0.4 * len(corr_cols) + 3, 0.4 * len(corr_cols) + 3))
    im = ax.imshow(corr_matrix, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(len(corr_cols)))
    ax.set_xticklabels(corr_cols, rotation=90, fontsize=7)
    ax.set_yticks(range(len(corr_cols)))
    ax.set_yticklabels(corr_cols, fontsize=7)
    ax.set_title("Pearson Correlation Heatmap (numeric FEATURE_COLUMNS + Target)")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    _save_fig(fig, FIG_DIR / "correlation_heatmap.png")

    target_corr = corr_matrix[target_col].drop(target_col).sort_values(ascending=False)
    print(f"Top positive correlations with '{target_col}':")
    print(target_corr.head(10).to_string())
    print(f"\nTop negative correlations with '{target_col}':")
    print(target_corr.tail(10).sort_values().to_string())

    print()
    return corr_matrix, target_corr

# Part 7 -- Mutual Information

def mutual_information_analysis(
    df: pd.DataFrame,
    numeric_cols: list[str],
    categorical_cols: list[str],
    boolean_cols: list[str],
    target_col: str = TARGET_COLUMN,
    random_state: int = 42,
) -> pd.DataFrame:
    
    print("=" * 70)
    print("PART 7 -- MUTUAL INFORMATION (FEATURE_COLUMNS vs. Target)")
    print("=" * 70)

    feature_cols = numeric_cols + categorical_cols + boolean_cols
    y = df[target_col]
    valid_rows = y.notna()

    X = pd.DataFrame(index=df.index[valid_rows])
    discrete_mask: list[bool] = []

    if numeric_cols:
        imputer = SimpleImputer(strategy="median")
        numeric_imputed = imputer.fit_transform(df.loc[valid_rows, numeric_cols])
        for i, col in enumerate(numeric_cols):
            X[col] = numeric_imputed[:, i]
            discrete_mask.append(False)

    for col in categorical_cols:
        filled = df.loc[valid_rows, col].fillna("__missing__")
        codes, _ = pd.factorize(filled)
        X[col] = codes
        discrete_mask.append(True)

    for col in boolean_cols:
        X[col] = df.loc[valid_rows, col].astype(int)
        discrete_mask.append(True)

    mi_scores = mutual_info_regression(
        X[feature_cols], y[valid_rows], discrete_features=discrete_mask, random_state=random_state
    )
    result = pd.DataFrame({"feature": feature_cols, "mutual_info": mi_scores}) \
        .sort_values("mutual_info", ascending=False) \
        .reset_index(drop=True)

    print(result.to_string(index=False))

    fig, ax = plt.subplots(figsize=(8, max(4, 0.3 * len(result))))
    ax.barh(result["feature"], result["mutual_info"], color="steelblue")
    ax.set_xlabel("Mutual Information")
    ax.set_title(f"Mutual Information: FEATURE_COLUMNS vs. {target_col}")
    ax.invert_yaxis()
    _save_fig(fig, FIG_DIR / "mutual_information.png")

    print()
    return result


# Part 8 -- Categorical Feature Analysis

def categorical_analysis(
    df: pd.DataFrame,
    categorical_cols: list[str],
    target_col: str = TARGET_COLUMN,
) -> dict[str, pd.DataFrame]:
   
    print("=" * 70)
    print("PART 8 -- CATEGORICAL FEATURE ANALYSIS")
    print("=" * 70)

    results: dict[str, pd.DataFrame] = {}

    for col in categorical_cols:
        summary = (
            df.groupby(col)[target_col]
              .agg(mean_runs="mean", median_runs="median", n="count")
              .sort_values("mean_runs", ascending=False)
        )
        print(f"\nMean {target_col} by '{col}':")
        print(summary.to_string())
        results[col] = summary

        fig, ax = plt.subplots(figsize=(max(5, 0.6 * len(summary)), 4.5))
        ax.bar(summary.index.astype(str), summary["mean_runs"], color="steelblue")
        ax.set_ylabel(f"Mean {target_col}")
        ax.set_title(f"Mean {target_col} by {col}")
        ax.tick_params(axis="x", rotation=45)
        _save_fig(fig, CAT_DIR / f"mean_runs_by_{col}.png")

    print()
    return results

# Part 9 -- Outlier Detection (report-only, never removes data)

def detect_outliers(
    df: pd.DataFrame, numeric_cols: list[str], target_col: str = TARGET_COLUMN
) -> pd.DataFrame:
    
    print("=" * 70)
    print("PART 9 -- OUTLIER DETECTION (IQR and Z-score; counts only)")
    print("=" * 70)

    cols_to_check = numeric_cols + [target_col]
    rows = []
    for col in cols_to_check:
        values = df[col].dropna()
        if values.empty:
            continue

        q1, q3 = values.quantile(0.25), values.quantile(0.75)
        iqr = q3 - q1
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        iqr_outliers = int(((values < lower) | (values > upper)).sum())

        z_scores = stats.zscore(values, nan_policy="omit")
        zscore_outliers = int((np.abs(z_scores) > 3).sum())

        rows.append({
            "column": col,
            "iqr_outliers": iqr_outliers,
            "iqr_pct": round(iqr_outliers / len(values) * 100, 2),
            "zscore_outliers": zscore_outliers,
            "zscore_pct": round(zscore_outliers / len(values) * 100, 2),
        })

    report = pd.DataFrame(rows).sort_values("iqr_outliers", ascending=False).reset_index(drop=True)
    print(report.to_string(index=False))
    print()
    return report


# Part 10 -- Multicollinearity (Variance Inflation Factor)

def _compute_vif(X: pd.DataFrame) -> pd.DataFrame:
   
    rows = []
    for col in X.columns:
        y = X[col]
        others = X.drop(columns=[col])
        r2 = LinearRegression().fit(others, y).score(others, y)
        vif = np.inf if r2 >= 1.0 else 1.0 / (1.0 - r2)
        rows.append({"feature": col, "VIF": vif})
    return pd.DataFrame(rows).sort_values("VIF", ascending=False).reset_index(drop=True)


def multicollinearity_vif(df: pd.DataFrame, numeric_cols: list[str]) -> pd.DataFrame:
    
    print("=" * 70)
    print("PART 10 -- MULTICOLLINEARITY (VARIANCE INFLATION FACTOR)")
    print("=" * 70)

    imputer = SimpleImputer(strategy="median")
    X_imputed = pd.DataFrame(imputer.fit_transform(df[numeric_cols]), columns=numeric_cols)

    vif_df = _compute_vif(X_imputed)
    vif_df["flag_gt5"] = vif_df["VIF"] > 5
    vif_df["flag_gt10"] = vif_df["VIF"] > 10

    print(vif_df.to_string(index=False))
    print(f"\nFeatures with VIF > 5:  {vif_df.loc[vif_df['flag_gt5'], 'feature'].tolist()}")
    print(f"Features with VIF > 10: {vif_df.loc[vif_df['flag_gt10'], 'feature'].tolist()}")
    print("(Reported only -- no features have been removed.)\n")

    return vif_df


# Part 11 -- Feature Engineering Validation
#
# Independently re-verifies the leakage-safety claims feature_engineering.py
# makes about itself, rather than trusting its own self-report. Uses
# CAREER_FEATURES / RECENT_FORM_FEATURES / SORT_COLUMNS imported from
# feature_engineering.py so this check can never drift from what that
# module actually produces.

def validate_feature_engineering(df: pd.DataFrame) -> dict[str, Any]:
    
    print("=" * 70)
    print("PART 11 -- FEATURE ENGINEERING VALIDATION (leakage-safety re-check)")
    print("=" * 70)

    ordered = df.sort_values(SORT_COLUMNS)
    first_rows = ordered.groupby(RAW_PLAYER_COLUMN).head(1)
    results: dict[str, Any] = {}

    # 1. First-innings checks
    non_zero_first_innings = int((first_rows["career_innings"] != 0).sum())
    non_zero_first_runs = int((first_rows["career_runs"] != 0).sum())
    non_null_first_avg = int(first_rows["career_average"].notna().sum())
    recent_form_cols = [c for c in RECENT_FORM_FEATURES if c in first_rows.columns]
    non_null_recent_first = {
        c: int(first_rows[c].notna().sum())
        for c in recent_form_cols
        if first_rows[c].notna().sum() > 0
    }

    print("First-innings checks:")
    print(f"  career_innings == 0 for all first innings : "
          f"{'PASS' if non_zero_first_innings == 0 else f'FAIL ({non_zero_first_innings} violation(s))'}")
    print(f"  career_runs == 0 for all first innings     : "
          f"{'PASS' if non_zero_first_runs == 0 else f'FAIL ({non_zero_first_runs} violation(s))'}")
    print(f"  career_average is null on first innings    : "
          f"{'PASS' if non_null_first_avg == 0 else f'FAIL ({non_null_first_avg} violation(s))'}")
    print(f"  recent-form features null on first innings : "
          f"{'PASS' if not non_null_recent_first else f'FAIL {non_null_recent_first}'}")

    results["first_innings_career_innings_violations"] = non_zero_first_innings
    results["first_innings_career_runs_violations"] = non_zero_first_runs
    results["first_innings_career_average_violations"] = non_null_first_avg
    results["first_innings_recent_form_violations"] = non_null_recent_first

    # --- 2. Monotonic non-decreasing counters
    monotonic_issues: dict[str, int] = {}
    for col in ["career_innings", "career_runs", "career_centuries", "career_fifties"]:
        if col not in df.columns:
            continue
        diffs = ordered.groupby(RAW_PLAYER_COLUMN)[col].diff()
        n_decreases = int((diffs < 0).sum())
        if n_decreases:
            monotonic_issues[col] = n_decreases

    print("\nMonotonic (non-decreasing) career counters:")
    if monotonic_issues:
        print(f"  FAIL -- decreasing values found: {monotonic_issues}")
    else:
        print("  PASS -- career_innings/career_runs/career_centuries/career_fifties "
              "never decrease within any player's history.")
    results["monotonic_counter_violations"] = monotonic_issues

    # 3. Independent recomputation of career_innings / career_runs 
    # Mirrors feature_engineering._shifted_expanding_stat()'s shift(1)
    # boundary, computed here independently (not by calling that function)
    # so this serves as a genuine cross-check rather than testing the same
    # code against itself.
    expected_career_innings = (
        ordered.groupby(RAW_PLAYER_COLUMN)[TARGET_COLUMN]
        .transform(lambda s: s.shift(1).expanding().count())
    )
    expected_career_runs = (
        ordered.groupby(RAW_PLAYER_COLUMN)[TARGET_COLUMN]
        .transform(lambda s: s.shift(1).expanding().sum())
        .fillna(0)
    )

    innings_mismatch = int(
        (~np.isclose(ordered["career_innings"], expected_career_innings, equal_nan=True)).sum()
    )
    runs_mismatch = int(
        (~np.isclose(ordered["career_runs"], expected_career_runs, equal_nan=True)).sum()
    )

    print("\nIndependent recomputation check (does career_* use only PRIOR innings?):")
    print(f"  career_innings matches independent recomputation : "
          f"{'PASS' if innings_mismatch == 0 else f'FAIL ({innings_mismatch} mismatch(es))'}")
    print(f"  career_runs matches independent recomputation     : "
          f"{'PASS' if runs_mismatch == 0 else f'FAIL ({runs_mismatch} mismatch(es))'}")
    results["career_innings_recomputation_mismatches"] = innings_mismatch
    results["career_runs_recomputation_mismatches"] = runs_mismatch

    print()
    return results


# Part 12 -- Leakage Validation


def validate_no_leakage() -> dict[str, Any]:
    
    print("=" * 70)
    print("PART 12 -- LEAKAGE VALIDATION")
    print("=" * 70)

    failures: list[str] = []

    if TARGET_COLUMN in FEATURE_COLUMNS:
        failures.append(f"Target column '{TARGET_COLUMN}' is present in FEATURE_COLUMNS.")

    leaked = [c for c in LEAKAGE_COLUMNS if c in FEATURE_COLUMNS]
    if leaked:
        failures.append(f"Leakage column(s) present in FEATURE_COLUMNS: {leaked}")

    if OLD_TARGET_COLUMN in FEATURE_COLUMNS:
        failures.append(f"Old target design '{OLD_TARGET_COLUMN}' is present in FEATURE_COLUMNS.")

    toss_columns = [c for c in FEATURE_COLUMNS if "toss" in c.lower()]
    if toss_columns:
        failures.append(f"Toss-related column(s) present in FEATURE_COLUMNS: {toss_columns}")

    if failures:
        message = "Leakage validation FAILED:\n  - " + "\n  - ".join(failures)
        raise RuntimeError(message)

    print(f"FEATURE_COLUMNS ({len(FEATURE_COLUMNS)} columns) checked against:")
    print(f"  - Target column                 : '{TARGET_COLUMN}' -- absent")
    print(f"  - LEAKAGE_COLUMNS (train_model.py): {LEAKAGE_COLUMNS} -- all absent")
    print(f"  - Old target design              : '{OLD_TARGET_COLUMN}' -- absent")
    print("  - Toss-related columns (any casing) -- absent")
    print("\nPASS -- no leakage columns found in FEATURE_COLUMNS.\n")

    return {"leakage_detected": False, "checked_columns": list(LEAKAGE_COLUMNS)}


# Part 13 -- Dataset Coverage

def dataset_coverage(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
   
    print("=" * 70)
    print("PART 13 -- DATASET COVERAGE")
    print("=" * 70)

    year = df[DATE_COLUMN].dt.year

    matches_per_year = (
        df.assign(_year=year)
          .groupby("_year")[RAW_MATCH_ID_COLUMN].nunique()
          .rename("unique_matches")
          .reset_index()
          .rename(columns={"_year": "year"})
    )
    players_per_year = (
        df.assign(_year=year)
          .groupby("_year")[RAW_PLAYER_COLUMN].nunique()
          .rename("unique_players")
          .reset_index()
          .rename(columns={"_year": "year"})
    )
    opponent_distribution = (
        df[RAW_OPPONENT_COLUMN].value_counts().rename("innings_count").reset_index()
        .rename(columns={"index": RAW_OPPONENT_COLUMN})
    )
    venue_distribution = (
        df[RAW_VENUE_COLUMN].value_counts().rename("innings_count").reset_index()
        .rename(columns={"index": RAW_VENUE_COLUMN})
    )
    home_away_distribution = (
        df["home_or_away"].value_counts().rename("innings_count").reset_index()
        .rename(columns={"index": "home_or_away"})
    )

    print("Matches per year:")
    print(matches_per_year.to_string(index=False))
    print("\nPlayers per year:")
    print(players_per_year.to_string(index=False))
    print("\nOpponent distribution:")
    print(opponent_distribution.to_string(index=False))
    print("\nVenue distribution:")
    print(venue_distribution.to_string(index=False))
    print("\nHome / Away distribution:")
    print(home_away_distribution.to_string(index=False))

    tables = {
        "matches_per_year": matches_per_year,
        "players_per_year": players_per_year,
        "opponent_distribution": opponent_distribution,
        "venue_distribution": venue_distribution,
        "home_away_distribution": home_away_distribution,
    }
    for name, table in tables.items():
        table.to_csv(COVERAGE_DIR / f"{name}.csv", index=False)
    print(f"\nSaved coverage tables to '{COVERAGE_DIR}'\n")

    return tables

# Part 14 -- Feature Readiness Report


def feature_readiness_report(
    numeric_cols: list[str],
    categorical_cols: list[str],
    boolean_cols: list[str],
    missing_report: pd.DataFrame,
    target_corr: pd.Series,
    mi_report: pd.DataFrame,
    vif_report: pd.DataFrame,
    leakage_result: dict[str, Any],
    top_n: int = 5,
) -> dict[str, Any]:
    """Consolidated, thesis-ready summary of dataset readiness for modelling."""
    print("=" * 70)
    print("PART 14 -- FEATURE READINESS REPORT")
    print("=" * 70)

    total_missing = int(missing_report["missing_count"].sum())
    high_vif_features = vif_report.loc[vif_report["flag_gt5"], "feature"].tolist()

    print(f"Numeric features       : {len(numeric_cols)}")
    print(f"Categorical features   : {len(categorical_cols)}")
    print(f"Boolean features       : {len(boolean_cols)}")
    print(f"Total features         : {len(numeric_cols) + len(categorical_cols) + len(boolean_cols)}")
    print(f"Target variable        : {TARGET_COLUMN}")
    print(f"Total missing values   : {total_missing:,} (across FEATURE_COLUMNS + target)")
    print(f"Potential multicollinearity (VIF > 5): {high_vif_features if high_vif_features else 'none'}")
    print(f"Potential leakage       : {'DETECTED' if leakage_result['leakage_detected'] else 'none'}")

    print(f"\nTop {top_n} positively correlated features with {TARGET_COLUMN}:")
    print(target_corr.head(top_n).to_string())
    print(f"\nTop {top_n} negatively correlated features with {TARGET_COLUMN}:")
    print(target_corr.tail(top_n).sort_values().to_string())

    print(f"\nTop {top_n} features by Mutual Information:")
    print(mi_report.head(top_n).to_string(index=False))

    print(f"\nHighest-VIF features:")
    print(vif_report.head(top_n).to_string(index=False))
    print()

    return {
        "numeric_feature_count": len(numeric_cols),
        "categorical_feature_count": len(categorical_cols),
        "boolean_feature_count": len(boolean_cols),
        "target_variable": TARGET_COLUMN,
        "total_missing_values": total_missing,
        "high_vif_features": high_vif_features,
        "leakage_detected": leakage_result["leakage_detected"],
        "top_positive_correlations": target_corr.head(top_n).to_dict(),
        "top_negative_correlations": target_corr.tail(top_n).sort_values().to_dict(),
        "top_mutual_information": mi_report.head(top_n).to_dict(orient="records"),
    }

# Orchestration

def main() -> None:
    """Run the full EDA pipeline end-to-end and persist all outputs.
    Read-only with respect to final_ml_dataset.csv throughout."""
    ensure_output_dirs()

    df = load_dataset(ML_OUTPUT_FILE)

    # Part 1-2: overview + feature-list validation (hard-fails on mismatch)
    dataset_summary = dataset_overview(df)
    feature_validation = validate_feature_columns(df)

    # Single point of feature-type classification -- every later Part
    # reuses these three lists rather than re-deriving or hardcoding them.
    numeric_cols, categorical_cols, boolean_cols = classify_feature_types(df)
    print(f"Feature type classification -- numeric: {len(numeric_cols)}, "
          f"categorical: {len(categorical_cols)}, boolean: {len(boolean_cols)}\n")

    # Part 3-10: descriptive + diagnostic analysis
    missing_report = missing_value_analysis(df)
    target_variable_analysis(df)
    plot_numerical_distributions(df, numeric_cols)
    corr_matrix, target_corr = correlation_analysis(df, numeric_cols, boolean_cols)
    mi_report = mutual_information_analysis(df, numeric_cols, categorical_cols, boolean_cols)
    categorical_analysis(df, categorical_cols)
    outlier_report = detect_outliers(df, numeric_cols)
    vif_report = multicollinearity_vif(df, numeric_cols)

    # Part 11-12: leakage-safety re-verification (independent of
    # feature_engineering.py's own self-checks) and the hard leakage gate.
    fe_validation = validate_feature_engineering(df)
    leakage_result = validate_no_leakage()

    # Part 13: coverage tables for the thesis
    dataset_coverage(df)

    # Part 14: consolidated summary
    readiness = feature_readiness_report(
        numeric_cols, categorical_cols, boolean_cols,
        missing_report, target_corr, mi_report, vif_report, leakage_result,
    )

    # Save CSV outputs (never the dataset itself)
    dataset_summary.to_csv(EDA_DIR / "dataset_summary.csv", index=False)
    missing_report.to_csv(EDA_DIR / "missing_values.csv", index=False)
    corr_matrix.to_csv(EDA_DIR / "correlation_matrix.csv")
    mi_report.to_csv(EDA_DIR / "mutual_information.csv", index=False)
    vif_report.to_csv(EDA_DIR / "vif_scores.csv", index=False)
    outlier_report.to_csv(EDA_DIR / "outlier_report.csv", index=False)

    import json
    with open(EDA_DIR / "feature_engineering_validation.json", "w", encoding="utf-8") as f:
        json.dump(fe_validation, f, indent=2, default=str)
    with open(EDA_DIR / "feature_readiness_report.json", "w", encoding="utf-8") as f:
        json.dump(readiness, f, indent=2, default=str)

    print(f"Saved CSV/JSON summaries and all plots under '{EDA_DIR}'")


if __name__ == "__main__":
    main()