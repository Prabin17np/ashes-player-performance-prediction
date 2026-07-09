from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import (
    HistGradientBoostingRegressor,
    RandomForestRegressor,
)
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LinearRegression
from sklearn.metrics import (
    explained_variance_score,
    max_error,
    mean_absolute_error,
    median_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.model_selection import RandomizedSearchCV, TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder

from ml.config import ML_OUTPUT_FILE, OUT_DIR

# Single source of truth for which engineered columns are approved model
# inputs. prepare_features() builds X ONLY from this whitelist -- it never
# infers features by dropping known-bad columns, which is what previously
# let duplicate raw/engineered columns (e.g. 'Venue' vs 'venue') and
# untracked columns (e.g. 'Team') leak into the model as spurious,
# perfectly collinear features.
from ml.feature_engineering import FEATURE_COLUMNS

# Optional boosting libraries -- the script must still run end-to-end if
# either is not installed, so both imports are guarded and their
# availability is checked before either is added as a candidate model.
# NOTE: a static analyzer (e.g. Pylance) may flag these two imports as
# "could not be resolved" if the packages aren't installed in the current
# environment. That is a static-analysis warning only, not a runtime
# error -- the try/except below is specifically designed so the script
# runs correctly either way, simply skipping the model if unavailable.
try:
    from xgboost import XGBRegressor
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBRegressor = None
    XGBOOST_AVAILABLE = False

try:
    from catboost import CatBoostRegressor
    CATBOOST_AVAILABLE = True
except ImportError:
    CatBoostRegressor = None
    CATBOOST_AVAILABLE = False

# Reproducibility / global configuration

RANDOM_SEED = 42
TARGET_COL = "Runs"
TRAIN_FRACTION = 0.8
N_CV_SPLITS = 5
N_RANDOM_SEARCH_ITER = 20
RUNS_BUCKET_EDGES = (0, 10, 50, 1000)
RUNS_BUCKET_LABELS = ("0-10", "11-50", "51+")

MODELS_DIR = OUT_DIR / "models"

IDENTIFIER_COLUMNS = ["Match_ID", "Player"]
DATE_COLUMN = "Match_Date"
MATCH_COLUMN = "Match_ID"

# Columns describing the current innings' own outcome -- must never enter X.
# Retained here (in addition to the FEATURE_COLUMNS whitelist) so
# validate_before_training() can explicitly name and check for each one,
# rather than relying solely on "not in the whitelist".
LEAKAGE_COLUMNS = [
    "Is_Dismissed",
    "Dismissal_Kind",
    "Dismissal_Bowler",
    "Dismissal_Fielders",
    "Match_Result",
    "Winning_Team",
    "Margin",
    "Toss_Winner",
    "Toss_Decision",
    "Balls_Faced",
]

# Relic of the earlier next-innings-prediction design. feature_engineering.py
# no longer produces this column at all, but it is guarded against here
# defensively in case an older cached copy of final_ml_dataset.csv is ever
# loaded by mistake -- it must never be treated as a feature or a target.
OLD_TARGET_COLUMN = "next_innings_runs"

# NOTE: no longer used to build X (see prepare_features()), kept only as
# documentation of columns that must never end up in the feature matrix.
COLUMNS_TO_DROP_FROM_FEATURES = (
    IDENTIFIER_COLUMNS + [DATE_COLUMN] + LEAKAGE_COLUMNS + [OLD_TARGET_COLUMN]
)

# PART 1 -- Load Dataset

def load_dataset(path: Path = ML_OUTPUT_FILE) -> pd.DataFrame:

    if not path.exists():
        raise FileNotFoundError(
            f"Engineered dataset not found at '{path}'. "
            "Run feature_engineering.py before train_model.py."
        )

    df = pd.read_csv(path)
    df[DATE_COLUMN] = pd.to_datetime(df[DATE_COLUMN])
    return df

# PART 2 -- Prepare Features

@dataclass
class FeatureSpec:
    target: str
    numeric_cols: list[str] = field(default_factory=list)
    categorical_cols: list[str] = field(default_factory=list)
    boolean_cols: list[str] = field(default_factory=list)

    @property
    def all_feature_cols(self) -> list[str]:
        return self.numeric_cols + self.categorical_cols + self.boolean_cols


def prepare_features(df: pd.DataFrame, target_col: str = TARGET_COL) -> tuple[pd.DataFrame, pd.Series, FeatureSpec]:
    
    if target_col not in df.columns:
        raise KeyError(f"Target column '{target_col}' not found in dataset.")

    missing_features = [c for c in FEATURE_COLUMNS if c not in df.columns]
    if missing_features:
        raise KeyError(
            f"Expected feature column(s) from FEATURE_COLUMNS are missing from the "
            f"dataset: {missing_features}. Regenerate '{ML_OUTPUT_FILE}' with the "
            "current feature_engineering.py before training."
        )

    y = df[target_col].copy()
    X = df[FEATURE_COLUMNS].copy()

    boolean_cols = [c for c in X.columns if pd.api.types.is_bool_dtype(X[c])]
    numeric_cols = [
        c for c in X.columns
        if pd.api.types.is_numeric_dtype(X[c]) and c not in boolean_cols
    ]
    categorical_cols = [
        c for c in X.columns
        if c not in boolean_cols and c not in numeric_cols
    ]

    spec = FeatureSpec(
        target=target_col,
        numeric_cols=numeric_cols,
        categorical_cols=categorical_cols,
        boolean_cols=boolean_cols,
    )

    print(f"Feature whitelist source : feature_engineering.FEATURE_COLUMNS ({len(FEATURE_COLUMNS)} columns)")
    print(f"Predictors retained : {len(spec.all_feature_cols)}")
    print(f"  Numeric     ({len(numeric_cols)}): {numeric_cols}")
    print(f"  Categorical ({len(categorical_cols)}): {categorical_cols}")
    print(f"  Boolean     ({len(boolean_cols)}): {boolean_cols}")

    return X[spec.all_feature_cols], y, spec


def build_feature_manifest(spec: FeatureSpec) -> dict[str, Any]:
    
    manifest = {
        "feature_columns": sorted(spec.all_feature_cols),
        "numeric_cols": sorted(spec.numeric_cols),
        "categorical_cols": sorted(spec.categorical_cols),
        "boolean_cols": sorted(spec.boolean_cols),
    }
    manifest_str = json.dumps(manifest, sort_keys=True)
    manifest["hash"] = hashlib.sha256(manifest_str.encode()).hexdigest()[:12]
    return manifest

# PART 2b Pre-training Leakage & Integrity Validation

def validate_before_training(
    df: pd.DataFrame,
    X: pd.DataFrame,
    spec: FeatureSpec,
    target_col: str = TARGET_COL,
) -> None:
    """Hard-fail integrity gate run once, before any model sees the data.

    Unlike a soft check that logs a warning and continues, every failure
    here raises immediately -- an undetected leak or malformed dataset
    should stop the run, not just be noted in a log a person might not read.
    """
    failures: list[str] = []

    # 1. Target exists in the source dataframe.
    if target_col not in df.columns:
        failures.append(f"Target column '{target_col}' is missing from the dataset.")

    # 2. Target itself never ends up as a predictor.
    if target_col in X.columns:
        failures.append(f"Target column '{target_col}' leaked into the feature matrix X.")

    # 3. The old next-innings target design is fully gone -- neither a
    #    feature, nor a target, nor anywhere in the source dataframe.
    if OLD_TARGET_COLUMN in X.columns:
        failures.append(f"'{OLD_TARGET_COLUMN}' (old target design) is present in X.")
    if OLD_TARGET_COLUMN in df.columns:
        print(
            f"NOTE: '{OLD_TARGET_COLUMN}' is present in the source dataframe but has "
            "been excluded from X -- consider regenerating final_ml_dataset.csv with "
            "the current feature_engineering.py so it isn't produced at all."
        )

    # 4. No current-innings-outcome column made it into X.
    leaked_columns = [c for c in LEAKAGE_COLUMNS if c in X.columns]
    if leaked_columns:
        failures.append(f"Leakage column(s) present in X: {leaked_columns}")

    # 4b. Toss information must never appear in X, under any name/casing.
    toss_columns = [c for c in X.columns if "toss" in c.lower()]
    if toss_columns:
        failures.append(f"Toss-related column(s) present in X: {toss_columns}")

    # 5. Whitelist enforcement -- X must match FEATURE_COLUMNS exactly.
    #    This is what catches the duplicate-column bug: a raw 'Venue'
    #    alongside engineered 'venue', an untracked 'Team' column, or any
    #    other column that isn't part of the approved feature set.
    unexpected_columns = [c for c in X.columns if c not in FEATURE_COLUMNS]
    if unexpected_columns:
        failures.append(
            f"Unexpected column(s) in X not present in FEATURE_COLUMNS whitelist: {unexpected_columns}"
        )

    missing_whitelisted = [c for c in FEATURE_COLUMNS if c not in X.columns]
    if missing_whitelisted:
        failures.append(
            f"FEATURE_COLUMNS whitelist entries missing from X: {missing_whitelisted}"
        )

    # 6. One row == one player innings.
    dup_key = ["Match_ID", "Player", "Innings_Number"]
    if all(c in df.columns for c in dup_key):
        dup_count = int(df.duplicated(subset=dup_key).sum())
        if dup_count:
            failures.append(
                f"{dup_count} duplicate row(s) on {dup_key} -- dataset is not one row per player innings."
            )
    else:
        failures.append(f"Cannot verify one-row-per-innings: missing column(s) from {dup_key}.")

    # 7. Match_Date exists and is fully populated (chronological split and
    #    TimeSeriesSplit both depend on this ordering being meaningful).
    if DATE_COLUMN not in df.columns:
        failures.append(f"Date column '{DATE_COLUMN}' is missing -- cannot verify chronological ordering.")
    elif df[DATE_COLUMN].isna().any():
        failures.append(f"{int(df[DATE_COLUMN].isna().sum())} null value(s) in '{DATE_COLUMN}'.")

    print(f"Pre-training validation: feature count = {len(spec.all_feature_cols)}")

    if failures:
        message = "Pre-training validation FAILED:\n  - " + "\n  - ".join(failures)
        raise RuntimeError(message)

    print("Pre-training validation: all checks passed (target present, no leakage "
          "columns in X, no toss information, no next_innings_runs, X matches "
          "FEATURE_COLUMNS whitelist exactly, one row per innings, dates valid).")


# PART 3 -- Preprocessing

def _bool_to_float(array: np.ndarray) -> np.ndarray:
    """Cast a boolean array to float so it can flow through a numeric
    sklearn pipeline unchanged in value (True/False -> 1.0/0.0)."""
    return np.asarray(array, dtype=float)


def build_preprocessor(spec: FeatureSpec) -> ColumnTransformer:

    numeric_pipeline = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="median")),
    ])

    categorical_pipeline = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore")),
    ])

    boolean_pipeline = Pipeline(steps=[
        ("to_float", FunctionTransformer(_bool_to_float, feature_names_out="one-to-one")),
    ])

    transformers = []
    if spec.numeric_cols:
        transformers.append(("numeric", numeric_pipeline, spec.numeric_cols))
    if spec.categorical_cols:
        transformers.append(("categorical", categorical_pipeline, spec.categorical_cols))
    if spec.boolean_cols:
        transformers.append(("boolean", boolean_pipeline, spec.boolean_cols))

    return ColumnTransformer(transformers=transformers, remainder="drop", sparse_threshold=0)

# PART 4 -- Time-aware Train/Test Split

def chronological_train_test_split(
    df: pd.DataFrame,
    X: pd.DataFrame,
    y: pd.Series,
    train_fraction: float = TRAIN_FRACTION,
    date_col: str = DATE_COLUMN,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
  
    order = df[date_col].sort_values(kind="mergesort").index
    dates_sorted = df.loc[order, date_col]

    unique_dates = np.sort(dates_sorted.unique())
    if len(unique_dates) < 2:
        raise ValueError("Need at least 2 distinct Match_Date values to create a train/test split.")

    split_pos = int(len(unique_dates) * train_fraction)
    split_pos = min(max(split_pos, 1), len(unique_dates) - 1)
    split_date = unique_dates[split_pos]

    train_mask = (dates_sorted < split_date).to_numpy()
    test_mask = ~train_mask

    train_idx = order[train_mask]
    test_idx = order[test_mask]

    X_train, X_test = X.loc[train_idx], X.loc[test_idx]
    y_train, y_test = y.loc[train_idx], y.loc[test_idx]

    train_dates = df.loc[train_idx, date_col]
    test_dates = df.loc[test_idx, date_col]

    # Hard guarantees: strictly chronological boundary, zero shared dates.
    assert train_dates.max() < test_dates.min(), (
        "Date leakage detected: training and testing sets overlap on Match_Date."
    )
    assert set(train_dates.unique()).isdisjoint(set(test_dates.unique())), (
        "Date leakage detected: a Match_Date value appears in both train and test."
    )
    # TimeSeriesSplit (used later for CV/tuning) assumes X_train's row order
    # is chronological. Boolean-masking a date-sorted index preserves order,
    # but this assertion makes that assumption explicit rather than implicit.
    assert train_dates.is_monotonic_increasing, (
        "X_train rows are not in chronological order; TimeSeriesSplit requires this."
    )

    print(f"Training rows        : {len(X_train):,}")
    print(f"Testing rows          : {len(X_test):,}")
    print(f"Training unique dates : {train_dates.nunique():,}")
    print(f"Testing unique dates  : {test_dates.nunique():,}")
    print(f"Training date range   : {train_dates.min().date()} -> {train_dates.max().date()}")
    print(f"Testing date range    : {test_dates.min().date()} -> {test_dates.max().date()}")

    return X_train, X_test, y_train, y_test


def check_no_match_split(
    df: pd.DataFrame,
    train_idx: pd.Index,
    test_idx: pd.Index,
    match_col: str = MATCH_COLUMN,
) -> list[Any]:
    
    train_matches = set(df.loc[train_idx, match_col])
    test_matches = set(df.loc[test_idx, match_col])
    overlap = sorted(train_matches & test_matches)

    if overlap:
        preview = overlap[:5]
        print(f"NOTE: {len(overlap)} match(es) have innings in both train and test "
              f"(date-based split can split a multi-day match): {preview}"
              f"{'...' if len(overlap) > 5 else ''}")
    else:
        print("No match is split across train/test (every Match_ID falls entirely "
              "on one side of the date boundary).")

    return overlap


def report_cold_start_players(df: pd.DataFrame, test_idx: pd.Index) -> None:
  
    if "career_innings" not in df.columns or len(test_idx) == 0:
        return
    cold_start_count = int((df.loc[test_idx, "career_innings"] == 0).sum())
    share = cold_start_count / len(test_idx)
    print(f"Test rows with zero prior career innings (cold start): "
          f"{cold_start_count:,} / {len(test_idx):,} ({share:.1%})")

# PART 5  Candidate Models

def build_candidate_models(random_seed: int = RANDOM_SEED) -> dict[str, Any]:

    models: dict[str, Any] = {
        "DummyRegressor": DummyRegressor(strategy="mean"),
        "LinearRegression": LinearRegression(),
        "RandomForestRegressor": RandomForestRegressor(
            n_estimators=300,
            max_depth=8,
            min_samples_leaf=5,
            random_state=random_seed,
            n_jobs=-1,
        ),
        "HistGradientBoostingRegressor": HistGradientBoostingRegressor(
            max_depth=6,
            learning_rate=0.05,
            max_iter=200,
            l2_regularization=1.0,
            random_state=random_seed,
        ),
    }

    if XGBOOST_AVAILABLE:
        models["XGBRegressor"] = XGBRegressor(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=random_seed,
            n_jobs=-1,
        )
    else:
        print("XGBoost not installed -- skipping XGBRegressor.")

    if CATBOOST_AVAILABLE:
        # Fed through the same ColumnTransformer as every other model here
        # (median-imputed numeric + one-hot-encoded categorical), rather
        # than CatBoost's native cat_features handling -- kept consistent
        # with the existing shared-preprocessing architecture rather than
        # forking preprocessing per model.
        models["CatBoostRegressor"] = CatBoostRegressor(
            iterations=300,
            depth=6,
            learning_rate=0.05,
            random_state=random_seed,
            verbose=False,
        )
    else:
        print("CatBoost not installed -- skipping CatBoostRegressor.")

    return models


def build_model_pipeline(preprocessor: ColumnTransformer, estimator: Any) -> Pipeline:

    return Pipeline(steps=[
        ("preprocessor", preprocessor),
        ("model", estimator),
    ])

# PART 6 -- Cross Validation

def _rmse_scorer(y_true: np.ndarray, y_pred: np.ndarray) -> float:

    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def cross_validate_model(
    pipeline: Pipeline,
    X: pd.DataFrame,
    y: pd.Series,
    n_splits: int = N_CV_SPLITS,
) -> dict[str, float]:

    splitter = TimeSeriesSplit(n_splits=n_splits)

    fold_mae, fold_rmse, fold_r2 = [], [], []

    for train_idx, val_idx in splitter.split(X):
        X_fold_train, X_fold_val = X.iloc[train_idx], X.iloc[val_idx]
        y_fold_train, y_fold_val = y.iloc[train_idx], y.iloc[val_idx]

        pipeline.fit(X_fold_train, y_fold_train)
        predictions = pipeline.predict(X_fold_val)

        fold_mae.append(mean_absolute_error(y_fold_val, predictions))
        fold_rmse.append(_rmse_scorer(y_fold_val, predictions))
        fold_r2.append(r2_score(y_fold_val, predictions))

    return {
        "mae": float(np.mean(fold_mae)),
        "rmse": float(np.mean(fold_rmse)),
        "r2": float(np.mean(fold_r2)),
    }

# PART 7 -- Hyperparameter Tuning

def _param_grid_random_forest() -> dict[str, list[Any]]:
    return {
        "model__n_estimators": [200, 300, 400],
        "model__max_depth": [4, 6, 8, 12, None],
        "model__min_samples_leaf": [1, 3, 5, 10],
        "model__max_features": ["sqrt", "log2", 0.5],
    }


def _param_grid_hist_gbm() -> dict[str, list[Any]]:
    return {
        "model__max_depth": [3, 4, 6, None],
        "model__learning_rate": [0.02, 0.05, 0.1],
        "model__max_iter": [100, 200, 300],
        "model__l2_regularization": [0.0, 0.5, 1.0],
    }


def _param_grid_xgboost() -> dict[str, list[Any]]:
    return {
        "model__n_estimators": [200, 300, 400, 600],
        "model__max_depth": [3, 4, 6, 8],
        "model__learning_rate": [0.01, 0.03, 0.05, 0.1],
        "model__subsample": [0.6, 0.8, 1.0],
        "model__colsample_bytree": [0.6, 0.8, 1.0],
    }


def _param_grid_catboost() -> dict[str, list[Any]]:
    return {
        "model__iterations": [200, 300, 500],
        "model__depth": [4, 6, 8, 10],
        "model__learning_rate": [0.01, 0.03, 0.05, 0.1],
        "model__l2_leaf_reg": [1, 3, 5, 10],
    }


TUNABLE_PARAM_GRIDS: dict[str, Any] = {
    "RandomForestRegressor": _param_grid_random_forest,
    "HistGradientBoostingRegressor": _param_grid_hist_gbm,
}
if XGBOOST_AVAILABLE:
    TUNABLE_PARAM_GRIDS["XGBRegressor"] = _param_grid_xgboost
if CATBOOST_AVAILABLE:
    TUNABLE_PARAM_GRIDS["CatBoostRegressor"] = _param_grid_catboost

# Models evaluated with default hyperparameters only (not tuned) -- kept as
# a fixed baseline pair so DummyRegressor/LinearRegression always provide
# an untuned reference point in the comparison table.
NON_TUNED_MODEL_NAMES = ["DummyRegressor", "LinearRegression"]


def tune_model(
    pipeline: Pipeline,
    param_grid: dict[str, list[Any]],
    X: pd.DataFrame,
    y: pd.Series,
    n_splits: int = N_CV_SPLITS,
    n_iter: int = N_RANDOM_SEARCH_ITER,
    random_seed: int = RANDOM_SEED,
) -> RandomizedSearchCV:

    splitter = TimeSeriesSplit(n_splits=n_splits)

    search = RandomizedSearchCV(
        estimator=pipeline,
        param_distributions=param_grid,
        n_iter=n_iter,
        scoring="neg_mean_absolute_error",
        cv=splitter,
        random_state=random_seed,
        n_jobs=-1,
        refit=True,
    )
    search.fit(X, y)
    return search

# PART 8 -- Final Evaluation

def evaluate_on_test_set(
    pipeline: Pipeline,
    X_test: pd.DataFrame,
    y_test: pd.Series,
) -> dict[str, float]:
    
    predictions = pipeline.predict(X_test)

    return {
        "mae": float(mean_absolute_error(y_test, predictions)),
        "median_ae": float(median_absolute_error(y_test, predictions)),
        "mse": float(mean_squared_error(y_test, predictions)),
        "rmse": _rmse_scorer(y_test.to_numpy(), predictions),
        "r2": float(r2_score(y_test, predictions)),
        "explained_variance": float(explained_variance_score(y_test, predictions)),
        "max_error": float(max_error(y_test, predictions)),
    }


def error_by_runs_bucket(
    y_true: pd.Series,
    y_pred: np.ndarray,
    bins: tuple[int, ...] = RUNS_BUCKET_EDGES,
    labels: tuple[str, ...] = RUNS_BUCKET_LABELS,
) -> pd.DataFrame:
   
    y_true_arr = pd.Series(np.asarray(y_true), name="actual").reset_index(drop=True)
    y_pred_arr = pd.Series(np.asarray(y_pred), name="predicted").reset_index(drop=True)
    bucket = pd.cut(y_true_arr, bins=bins, labels=labels, right=True, include_lowest=True)

    rows = []
    for label in labels:
        mask = (bucket == label).to_numpy()
        if mask.sum() == 0:
            continue
        rows.append({
            "Runs bucket": label,
            "Count": int(mask.sum()),
            "MAE": float(mean_absolute_error(y_true_arr[mask], y_pred_arr[mask])),
            "RMSE": _rmse_scorer(y_true_arr[mask].to_numpy(), y_pred_arr[mask].to_numpy()),
        })
    return pd.DataFrame(rows)


def skill_score(model_mae: float, baseline_mae: float) -> float:
    return 1.0 - (model_mae / baseline_mae)

# PART 9 -- Model Comparison

def build_comparison_table(
    cv_results: dict[str, dict[str, float]],
    test_results: dict[str, dict[str, float]],
    training_times: dict[str, float],
) -> pd.DataFrame:

    rows = []
    for model_name, cv_metrics in cv_results.items():
        test_metrics = test_results.get(model_name, {})
        rows.append({
            "Model": model_name,
            "CV MAE": cv_metrics["mae"],
            "CV RMSE": cv_metrics["rmse"],
            "CV R2": cv_metrics["r2"],
            "Test MAE": test_metrics.get("mae", np.nan),
            "Test RMSE": test_metrics.get("rmse", np.nan),
            "Test R2": test_metrics.get("r2", np.nan),
            "Training Time": training_times.get(model_name, np.nan),
        })
    return pd.DataFrame(rows).sort_values("CV MAE").reset_index(drop=True)

# PART 10 -- Feature Importance

def extract_feature_importance(
    pipeline: Pipeline,
    model_name: str,
    X_test: pd.DataFrame | None = None,
    y_test: pd.Series | None = None,
) -> tuple[pd.DataFrame | None, str | None]:

    preprocessor: ColumnTransformer = pipeline.named_steps["preprocessor"]
    model = pipeline.named_steps["model"]

    try:
        feature_names = preprocessor.get_feature_names_out()
    except (AttributeError, ValueError):
        feature_names = None

    if hasattr(model, "feature_importances_"):
        importances = model.feature_importances_
        method: str | None = "native"
    elif hasattr(model, "coef_"):
        importances = np.abs(np.ravel(model.coef_))
        method = "coefficient"
    elif X_test is not None and y_test is not None:

        X_test_transformed = preprocessor.transform(X_test)
        perm_result = permutation_importance(
            model,
            X_test_transformed,
            y_test,
            n_repeats=20,
            random_state=RANDOM_SEED,
            scoring="neg_mean_absolute_error",
            n_jobs=-1,
        )
        importances = perm_result.importances_mean
        method = "permutation"
        print(
            f"Model '{model_name}' exposes neither feature_importances_ "
            "nor coef_ -- using model-agnostic Permutation Feature "
            "Importance instead (n_repeats=20, scoring=neg_mean_absolute_error)."
        )
    else:
        return None, None

    if feature_names is None or len(feature_names) != len(importances):
        feature_names = [f"feature_{i}" for i in range(len(importances))]

    table = pd.DataFrame({"Feature": feature_names, "Importance": importances})
    return table.sort_values("Importance", ascending=False).reset_index(drop=True), method

# PART 11 -- Save Artifacts

def save_artifacts(
    pipeline: Pipeline,
    preprocessor: ColumnTransformer,
    metadata: dict[str, Any],
    models_dir: Path = MODELS_DIR,
) -> None:

    models_dir.mkdir(parents=True, exist_ok=True)

    joblib.dump(pipeline.named_steps["model"], models_dir / "best_model.pkl")
    joblib.dump(preprocessor, models_dir / "preprocessor.pkl")

    with open(models_dir / "training_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, default=str)

    print(f"Saved model      -> '{models_dir / 'best_model.pkl'}'")
    print(f"Saved preprocessor -> '{models_dir / 'preprocessor.pkl'}'")
    print(f"Saved metadata   -> '{models_dir / 'training_metadata.json'}'")

# PART 12 -- Console Summary

def print_console_summary(
    df: pd.DataFrame,
    spec: FeatureSpec,
    train_dates: tuple[pd.Timestamp, pd.Timestamp],
    test_dates: tuple[pd.Timestamp, pd.Timestamp],
    models_evaluated: list[str],
    best_model_name: str,
    best_params: dict[str, Any],
    cv_metrics: dict[str, float],
    test_metrics: dict[str, float],
    models_dir: Path = MODELS_DIR,
) -> None:
    print("=" * 70)
    print("TRAINING RUN SUMMARY")
    print("=" * 70)
    print(f"Dataset shape        : {df.shape[0]:,} rows x {df.shape[1]} columns")
    print(f"Number of features   : {len(spec.all_feature_cols)}")
    print(f"Training period      : {train_dates[0].date()} -> {train_dates[1].date()}")
    print(f"Testing period       : {test_dates[0].date()} -> {test_dates[1].date()}")
    print(f"Models evaluated     : {models_evaluated}")
    print(f"Best model           : {best_model_name}")
    print(f"Best hyperparameters : {best_params if best_params else '(default -- not tuned)'}")
    print("\nCross-validation metrics (best model):")
    for key, value in cv_metrics.items():
        print(f"  {key.upper():<6}: {value:,.4f}")
    print("\nTest-set metrics (best model, evaluated once):")
    for key, value in test_metrics.items():
        print(f"  {key:<20}: {value:,.4f}")
    print(f"\nOutput directory     : '{models_dir}'")
    print("=" * 70)

# Orchestration

def main() -> None:
    """Run the full model training and evaluation pipeline end to end."""
    print("Starting model training pipeline\n")

    #  Part 1: Load
    df = load_dataset(ML_OUTPUT_FILE)
    print(f"Loaded {len(df):,} rows from '{ML_OUTPUT_FILE}'\n")

    # Part 2: Prepare features (explicit whitelist from FEATURE_COLUMNS)
    X, y, spec = prepare_features(df, TARGET_COL)
    print()

    # Part 2b: Hard-fail leakage & integrity gate -- must pass before any
    # model is fit.
    validate_before_training(df, X, spec, TARGET_COL)
    print()

    # Part 3: Preprocessing
    preprocessor = build_preprocessor(spec)

    #  Part 4: Chronological split (date-based, no shared dates)
    X_train, X_test, y_train, y_test = chronological_train_test_split(df, X, y)
    check_no_match_split(df, X_train.index, X_test.index)
    report_cold_start_players(df, X_test.index)
    print()

    train_dates = (
        df.loc[X_train.index, DATE_COLUMN].min(),
        df.loc[X_train.index, DATE_COLUMN].max(),
    )
    test_dates = (
        df.loc[X_test.index, DATE_COLUMN].min(),
        df.loc[X_test.index, DATE_COLUMN].max(),
    )

    #  Part 5: Candidate models
    candidate_models = build_candidate_models(RANDOM_SEED)
    print(f"Candidate models: {list(candidate_models.keys())}\n")

    #  Part 6: Cross-validate every candidate with default hyperparameters
    print("=" * 70)
    print("CROSS-VALIDATION (default hyperparameters)")
    print("=" * 70)
    default_cv_results: dict[str, dict[str, float]] = {}
    for model_name, estimator in candidate_models.items():
        pipeline = build_model_pipeline(preprocessor, estimator)
        metrics = cross_validate_model(pipeline, X_train, y_train)
        default_cv_results[model_name] = metrics
        print(f"  {model_name:<32} MAE={metrics['mae']:.3f}  "
              f"RMSE={metrics['rmse']:.3f}  R2={metrics['r2']:.3f}")
    print()

    # Part 7: Hyperparameter tuning (every model in TUNABLE_PARAM_GRIDS --
    # RandomForest and HistGradientBoosting always; XGBoost/CatBoost only
    # if installed)
    print("=" * 70)
    print(f"HYPERPARAMETER TUNING ({', '.join(TUNABLE_PARAM_GRIDS.keys())})")
    print("=" * 70)

    tuned_pipelines: dict[str, Pipeline] = {}
    tuned_cv_results: dict[str, dict[str, float]] = {}
    best_params_by_model: dict[str, dict[str, Any]] = {}

    for model_name in TUNABLE_PARAM_GRIDS:
        base_pipeline = build_model_pipeline(preprocessor, candidate_models[model_name])
        param_grid = TUNABLE_PARAM_GRIDS[model_name]()

        search = tune_model(base_pipeline, param_grid, X_train, y_train)
        tuned_pipelines[model_name] = search.best_estimator_
        best_params_by_model[model_name] = {
            key.replace("model__", ""): value for key, value in search.best_params_.items()
        }


        tuned_metrics = cross_validate_model(search.best_estimator_, X_train, y_train)
        tuned_cv_results[model_name] = tuned_metrics

        print(f"  {model_name:<32} best params: {best_params_by_model[model_name]}")
        print(f"    -> MAE={tuned_metrics['mae']:.3f}  "
              f"RMSE={tuned_metrics['rmse']:.3f}  R2={tuned_metrics['r2']:.3f}")
    print()


    # Non-tuned baselines (Dummy, Linear) keep their default-hyperparameter
    # pipeline and CV result; every tuned model (RF/HGB always, XGB/CatBoost
    # if installed) contributes its already-tuned pipeline and CV result.
    # Built generically so adding/removing an optional model doesn't require
    # touching multiple hardcoded key lists here.
    final_cv_results: dict[str, dict[str, float]] = {
        name: default_cv_results[name] for name in NON_TUNED_MODEL_NAMES
    }
    final_cv_results.update(tuned_cv_results)

    #  Part 8: Select best model by CV performance, fit once, evaluate once
    best_model_name = min(final_cv_results, key=lambda name: final_cv_results[name]["mae"])
    print(f"Best model selected by CV MAE: {best_model_name}\n")

    final_pipelines: dict[str, Pipeline] = {
        name: build_model_pipeline(preprocessor, candidate_models[name])
        for name in NON_TUNED_MODEL_NAMES
    }
    final_pipelines.update(tuned_pipelines)

    training_times: dict[str, float] = {}
    for model_name, pipeline in final_pipelines.items():
        start = time.perf_counter()
        pipeline.fit(X_train, y_train)
        training_times[model_name] = time.perf_counter() - start

    best_pipeline = final_pipelines[best_model_name]

    print("=" * 70)
    print("FINAL TEST-SET EVALUATION (best model only, evaluated once)")
    print("=" * 70)
    test_predictions = best_pipeline.predict(X_test)
    test_metrics = evaluate_on_test_set(best_pipeline, X_test, y_test)
    for key, value in test_metrics.items():
        print(f"  {key:<20}: {value:,.4f}")
    print()

    # Runs-bucket error breakdown -- separates "how well does it call low
    # scores" from "how well does it call big innings", which a single
    # aggregate MAE/RMSE hides.
    bucket_table = error_by_runs_bucket(y_test, test_predictions)
    print("Test-set error by runs bucket:")
    print(bucket_table.to_string(index=False))
    bucket_path = MODELS_DIR / "error_by_runs_bucket.csv"
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    bucket_table.to_csv(bucket_path, index=False)
    print(f"Saved runs-bucket error table -> '{bucket_path}'")
    print()

    # Skill score vs. the naive Dummy (mean-predicting) baseline, using CV
    # MAE for both so the comparison is apples-to-apples.
    dummy_cv_mae = final_cv_results["DummyRegressor"]["mae"]
    best_cv_mae = final_cv_results[best_model_name]["mae"]
    skill = skill_score(best_cv_mae, dummy_cv_mae)
    print(f"Skill score vs. Dummy baseline (CV MAE improvement): {skill:.1%}\n")

    all_test_results = {best_model_name: test_metrics}

    # Part 9: Model comparison table
    comparison_table = build_comparison_table(final_cv_results, all_test_results, training_times)
    comparison_path = MODELS_DIR / "model_comparison.csv"
    comparison_table.to_csv(comparison_path, index=False)
    print(f"Saved model comparison table -> '{comparison_path}'")
    print(comparison_table.to_string(index=False))
    print()

    importance_table, importance_method = extract_feature_importance(
        best_pipeline, best_model_name, X_test=X_test, y_test=y_test
    )
    importance_filename: str | None = None
    if importance_table is not None:
        importance_filename = "feature_importance.csv"
        importance_path = MODELS_DIR / importance_filename
        importance_table.to_csv(importance_path, index=False)
        print(f"Saved feature importance -> '{importance_path}'")
        if importance_method == "permutation":
            print(
                "Feature importance method: model-agnostic Permutation "
                "Feature Importance (computed once on the held-out test set)."
            )
    else:
        print(f"Model '{best_model_name}' exposes neither feature_importances_ "
              "nor coef_ -- skipping feature importance export.")
    print()

    # Part 11: Save artifacts
    best_params = best_params_by_model.get(best_model_name, {})
    metadata = {
        "training_date": pd.Timestamp.now().isoformat(),
        "dataset_size": int(len(df)),
        "number_of_features": len(spec.all_feature_cols),
        "target_variable": TARGET_COL,
        "best_model": best_model_name,
        "best_hyperparameters": best_params,
        "cross_validation_metrics": final_cv_results[best_model_name],
        "test_metrics": test_metrics,
        "skill_score_vs_dummy_cv_mae": skill,
        "random_seed": RANDOM_SEED,
        "feature_importance_method": importance_method,
        "feature_importance_file": importance_filename,
        "feature_manifest": build_feature_manifest(spec),
    }
    save_artifacts(best_pipeline, best_pipeline.named_steps["preprocessor"], metadata)
    print()

    # Part 12: Console summary
    print_console_summary(
        df=df,
        spec=spec,
        train_dates=train_dates,
        test_dates=test_dates,
        models_evaluated=list(candidate_models.keys()),
        best_model_name=best_model_name,
        best_params=best_params,
        cv_metrics=final_cv_results[best_model_name],
        test_metrics=test_metrics,
    )


if __name__ == "__main__":
    main()