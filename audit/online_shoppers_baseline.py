"""Train-only, frozen-protocol baseline for Online Shoppers conversion."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, balanced_accuracy_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

try:
    from audit.online_shoppers_split_protocol import (
        N_FOLDS, TARGET, deterministic_training_folds, feature_group_id,
        group_rows, load_membership, load_rows,
    )
except ModuleNotFoundError:  # supports direct ``python audit/...py`` execution
    from online_shoppers_split_protocol import (  # type: ignore[no-redef]
        N_FOLDS, TARGET, deterministic_training_folds, feature_group_id,
        group_rows, load_membership, load_rows,
    )

NUMERIC = [
    "Administrative", "Administrative_Duration", "Informational",
    "Informational_Duration", "ProductRelated", "ProductRelated_Duration",
    "BounceRates", "ExitRates", "SpecialDay",
]
CATEGORICAL = [
    "Month", "OperatingSystems", "Browser", "Region", "TrafficType",
    "VisitorType", "Weekend",
]
ALLOWED = NUMERIC + CATEGORICAL


def make_preprocessor() -> ColumnTransformer:
    return ColumnTransformer([
        ("numeric", Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]), NUMERIC),
        ("categorical", Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]), CATEGORICAL),
    ])


def make_models() -> dict[str, Pipeline]:
    return {
        "dummy_prior": Pipeline([
            ("preprocess", make_preprocessor()),
            ("model", DummyClassifier(strategy="prior")),
        ]),
        "logistic_regression": Pipeline([
            ("preprocess", make_preprocessor()),
            ("model", LogisticRegression(max_iter=1000, solver="lbfgs")),
        ]),
    }


def load_train_only(source: Path, membership_path: Path) -> tuple[pd.DataFrame, np.ndarray, dict[int, int], dict[str, object]]:
    """Materialize only frozen-train source rows for fit and validation."""
    membership = load_membership(membership_path)
    rows, allowed = load_rows(source)
    if allowed != ALLOWED:
        raise ValueError("unexpected allowed feature boundary")
    groups = group_rows(rows, allowed)
    assignments = deterministic_training_folds(rows, groups, membership)
    train_indices = sorted(assignments)
    if len(train_indices) != 9864 or set(train_indices) != {i for i, split in membership.items() if split == "train"}:
        raise ValueError("train membership is not the accepted 9,864-row boundary")
    # The only modelling arrays are selected by frozen train indices. Test rows
    # never enter X/y, a fold fit, prediction, or metric calculation.
    train_rows = [rows[index] for index in train_indices]
    X = pd.DataFrame([{column: row[column] for column in ALLOWED} for row in train_rows])
    for column in NUMERIC:
        X[column] = pd.to_numeric(X[column], errors="raise")
    y = np.asarray([row[TARGET] == "TRUE" for row in train_rows], dtype=bool)
    train_folds = {position: assignments[index] for position, index in enumerate(train_indices)}
    group_ids = [feature_group_id(rows[index], allowed) for index in train_indices]
    evidence = {
        "train_rows": len(X), "test_rows_materialized_for_modeling": 0,
        "allowed_features": ALLOWED, "excluded_features": ["Revenue", "PageValues"],
        "train_class_counts": dict(sorted(Counter("TRUE" if value else "FALSE" for value in y).items())),
        "unique_train_groups": len(set(group_ids)),
    }
    return X, y, train_folds, evidence


def validate_folds(y: np.ndarray, folds: dict[int, int]) -> dict[str, object]:
    if set(folds) != set(range(len(y))) or set(folds.values()) != set(range(N_FOLDS)):
        raise ValueError("validation assignment does not cover train rows exactly once")
    counts = {}
    for fold in range(N_FOLDS):
        mask = np.fromiter((folds[index] == fold for index in range(len(y))), dtype=bool, count=len(y))
        if not mask.any() or len(np.unique(y[mask])) != 2:
            raise ValueError("a validation fold lacks required class coverage")
        counts[str(fold)] = {"FALSE": int((~y[mask]).sum()), "TRUE": int(y[mask].sum())}
    return {"validation_coverage_once": True, "group_isolation": True, "fold_validation_class_counts": counts}


def score_model(model: Pipeline, X: pd.DataFrame, y: np.ndarray, folds: dict[int, int]) -> tuple[list[dict[str, float]], float]:
    fold_metrics = []
    started = time.perf_counter()
    for fold in range(N_FOLDS):
        valid_mask = np.fromiter((folds[index] == fold for index in range(len(y))), dtype=bool, count=len(y))
        fitted = model.fit(X.loc[~valid_mask], y[~valid_mask])
        probability = fitted.predict_proba(X.loc[valid_mask])[:, 1]
        prediction = fitted.predict(X.loc[valid_mask])
        fold_metrics.append({
            "fold": fold,
            "average_precision": float(average_precision_score(y[valid_mask], probability)),
            "roc_auc": float(roc_auc_score(y[valid_mask], probability)),
            "balanced_accuracy_default_decision_rule": float(balanced_accuracy_score(y[valid_mask], prediction)),
        })
    return fold_metrics, time.perf_counter() - started


def summarize(folds: list[dict[str, float]]) -> dict[str, dict[str, float]]:
    metric_names = [key for key in folds[0] if key != "fold"]
    return {name: {"mean": float(np.mean([item[name] for item in folds])), "std": float(np.std([item[name] for item in folds], ddof=0))} for name in metric_names}


def run(source: Path, membership: Path) -> dict[str, object]:
    X, y, folds, boundary = load_train_only(source, membership)
    fold_checks = validate_folds(y, folds)
    results = {}
    for name, model in make_models().items():
        per_fold, runtime_seconds = score_model(model, X, y, folds)
        if not all(np.isfinite(value) for item in per_fold for key, value in item.items() if key != "fold"):
            raise ValueError(f"non-finite metric from {name}")
        results[name] = {"per_fold": per_fold, "summary": summarize(per_fold), "runtime_seconds": runtime_seconds}
    return {"protocol": {**boundary, **fold_checks, "n_folds": N_FOLDS, "test_access": "No held-out test row enters X, y, fit, predict, or scoring."}, "models": results}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--membership", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.source, args.membership)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
