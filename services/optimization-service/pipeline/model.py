"""LightGBM priority classifier for block-planner.

Predicts priority_class from job features, as a stand-in for
_ground_truth_priority (data_gen.py) a real deployment wouldn't have direct
access to -- only the observable signals a real inspection system would
record, not a synthetic scoring formula with a hidden noise term.

Feature/leakage decision (deliberate, not an oversight): _ground_truth_priority
computes its score from six inputs -- days_overdue (0.25), defect_severity
(0.30), speed_restriction_active (0.20), recurrence_count (0.10),
traffic_density (0.10), section_speed_limit (0.05) -- plus injected Gaussian
noise. Those six are NOT leakage: they're real, independently-observable job
attributes that exist and are known *before* a priority is ever assigned,
exactly the signals a human triage process would use. Excluding them would
leave nothing causally connected to the label at all. The only things
excluded here are `id` (an identifier, not a feature) and `priority_class`
itself (the target). Everything else in jobs_df -- including features with
no causal role in the label (asset_age_years, days_since_last_maintenance,
defect_type, passenger_train_count, department, segment, line,
estimated_duration_min, day) -- is included, mirroring a real system where
you don't know in advance which signals are informative.
"""

import joblib
import numpy as np
import pandas as pd
import shap
from lightgbm import LGBMClassifier
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split

from src.config import DEFAULT_SEED, MODEL_TEST_SIZE, N_TRAINING_SEEDS, PRIORITY_WEIGHTS
from src.data_gen import generate_dataset

MODEL_PATH = "models/priority_classifier.joblib"
PRIORITY_ORDER = ["Critical", "High", "Medium", "Low"]

FEATURE_COLUMNS = [
    "department",
    "segment",
    "line",
    "estimated_duration_min",
    "days_overdue",
    "defect_severity",
    "asset_age_years",
    "traffic_density",
    "days_since_last_maintenance",
    "defect_type",
    "recurrence_count",
    "section_speed_limit",
    "passenger_train_count",
    "speed_restriction_active",
    "day",
]
CATEGORICAL_COLUMNS = ["department", "line", "defect_type"]

LGBM_PARAMS = dict(n_estimators=300, learning_rate=0.05, num_leaves=31, random_state=DEFAULT_SEED, verbose=-1)


def _prepare_features(jobs_df: pd.DataFrame, category_levels: dict[str, list] | None = None) -> pd.DataFrame:
    """Select and type FEATURE_COLUMNS. At scoring time, pass the training
    run's `category_levels` so categorical codes line up with what the
    model was fit on, even if this batch doesn't contain every category."""
    X = jobs_df[FEATURE_COLUMNS].copy()
    X["speed_restriction_active"] = X["speed_restriction_active"].astype(int)
    for col in CATEGORICAL_COLUMNS:
        categories = category_levels[col] if category_levels is not None else None
        X[col] = pd.Categorical(X[col], categories=categories) if categories else X[col].astype("category")
    return X


def generate_training_data(n_seeds: int = N_TRAINING_SEEDS) -> pd.DataFrame:
    """Concatenate jobs_df across n_seeds distinct scenarios."""
    return pd.concat([generate_dataset(seed=seed)[2] for seed in range(n_seeds)], ignore_index=True)


def train_priority_model(n_seeds: int = N_TRAINING_SEEDS) -> dict:
    """Train, evaluate on a held-out split, and save the classifier to MODEL_PATH.

    Returns a report dict: macro_f1, classification_report (per-class
    precision/recall/f1, sklearn's output_dict form), confusion_matrix,
    labels (row/column order for the confusion matrix), and test_jobs_df
    (the held-out rows, full columns, for downstream SHAP/inspection).
    """
    jobs_df = generate_training_data(n_seeds)
    X = _prepare_features(jobs_df)
    y = jobs_df["priority_class"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=MODEL_TEST_SIZE, random_state=DEFAULT_SEED, stratify=y
    )

    model = LGBMClassifier(**LGBM_PARAMS)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    category_levels = {col: X[col].cat.categories.tolist() for col in CATEGORICAL_COLUMNS}
    joblib.dump({"model": model, "category_levels": category_levels}, MODEL_PATH)

    return {
        "macro_f1": f1_score(y_test, y_pred, average="macro"),
        "classification_report": classification_report(y_test, y_pred, labels=PRIORITY_ORDER, output_dict=True),
        "confusion_matrix": confusion_matrix(y_test, y_pred, labels=PRIORITY_ORDER),
        "labels": PRIORITY_ORDER,
        "test_jobs_df": jobs_df.loc[X_test.index],
    }


def score_jobs(df: pd.DataFrame) -> pd.DataFrame:
    """Load the saved model and return predicted_priority_class plus a
    probability column per class, one row per job in df (job_id preserved)."""
    bundle = joblib.load(MODEL_PATH)
    model, category_levels = bundle["model"], bundle["category_levels"]
    X = _prepare_features(df, category_levels=category_levels)
    proba = model.predict_proba(X)
    predicted = model.classes_[proba.argmax(axis=1)]

    result = pd.DataFrame(proba, columns=[f"proba_{c}" for c in model.classes_], index=df.index)
    result.insert(0, "job_id", df["id"].values)
    result.insert(1, "predicted_priority_class", predicted)
    return result


def predicted_weights(df: pd.DataFrame) -> dict[str, int]:
    """Weights dict for schedule_solver from this model's predictions,
    mirroring src.solver.ground_truth_weights but from predicted rather
    than ground-truth priority_class."""
    scored = score_jobs(df)
    return dict(zip(scored["job_id"], scored["predicted_priority_class"].map(PRIORITY_WEIGHTS)))


def feature_importance(jobs_df: pd.DataFrame) -> pd.DataFrame:
    """Mean |SHAP value| per feature (averaged across the four classes),
    against the saved model, for the given jobs_df -- e.g. the training
    run's held-out test_jobs_df."""
    bundle = joblib.load(MODEL_PATH)
    model, category_levels = bundle["model"], bundle["category_levels"]
    X = _prepare_features(jobs_df, category_levels=category_levels)

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)
    # shap_values is (n_samples, n_features, n_classes) for this multiclass
    # model/shap version; average |value| over samples and classes.
    mean_abs = np.abs(shap_values).mean(axis=(0, 2))

    return (
        pd.DataFrame({"feature": X.columns, "mean_abs_shap": mean_abs})
        .sort_values("mean_abs_shap", ascending=False)
        .reset_index(drop=True)
    )
