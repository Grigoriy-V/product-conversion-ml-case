"""One final frozen-holdout evaluation for the selected Online Shoppers RF."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline

try:
    from audit.online_shoppers_audit import fingerprint, row_id, sha256_file
    from audit.online_shoppers_baseline import ALLOWED, CATEGORICAL, NUMERIC, make_preprocessor
    from audit.online_shoppers_model_comparison import RF_CONFIG
    from audit.online_shoppers_split_protocol import TARGET, group_rows, load_membership, load_rows, validate_holdout
except ModuleNotFoundError:
    from online_shoppers_audit import fingerprint, row_id, sha256_file  # type: ignore[no-redef]
    from online_shoppers_baseline import ALLOWED, CATEGORICAL, NUMERIC, make_preprocessor  # type: ignore[no-redef]
    from online_shoppers_model_comparison import RF_CONFIG  # type: ignore[no-redef]
    from online_shoppers_split_protocol import TARGET, group_rows, load_membership, load_rows, validate_holdout  # type: ignore[no-redef]


SOURCE_SHA256 = "b3055ee355f59134d851d32641183cb4a8b45def7124d2f50442a042f358e0d9"
MEMBERSHIP_SHA256 = "8dd85409ff57638ed5a8197cb2d0fe5d1d13ff90c59b6dbd83e08c475e2deee1"
TRAIN_FINGERPRINT = "bf86c7bcedc2636d892f4a567d364b04625ae7f8419e177a5e012e7083802d86"
TEST_FINGERPRINT = "88192976cbf6bcfef812ec1e474b21a019e6f101846701118b2e60070f1ed649"
DEFAULT_THRESHOLD = 0.5
SLICE_COLUMNS = ("VisitorType", "Weekend", "Month")


def make_model() -> Pipeline:
    return Pipeline([
        ("preprocess", make_preprocessor()),
        ("model", RandomForestClassifier(**RF_CONFIG)),
    ])


def _binary_metrics(y: np.ndarray, probability: np.ndarray) -> dict[str, object]:
    prediction = probability >= DEFAULT_THRESHOLD
    matrix = confusion_matrix(y, prediction, labels=[False, True])
    return {
        "average_precision": float(average_precision_score(y, probability)),
        "roc_auc": float(roc_auc_score(y, probability)),
        "balanced_accuracy_default_threshold_0_5": float(balanced_accuracy_score(y, prediction)),
        "precision_default_threshold_0_5": float(precision_score(y, prediction, zero_division=0)),
        "recall_default_threshold_0_5": float(recall_score(y, prediction, zero_division=0)),
        "f1_default_threshold_0_5": float(f1_score(y, prediction, zero_division=0)),
        "confusion_matrix_labels_false_true": matrix.astype(int).tolist(),
        "false_positives": int(matrix[0, 1]),
        "false_negatives": int(matrix[1, 0]),
        "predicted_positive": int(prediction.sum()),
    }


def _slice_metrics(values: pd.Series, y: np.ndarray, probability: np.ndarray) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for value in sorted(values.astype(str).unique()):
        mask = values.astype(str).to_numpy() == value
        y_slice = y[mask]
        probability_slice = probability[mask]
        prediction = probability_slice >= DEFAULT_THRESHOLD
        matrix = confusion_matrix(y_slice, prediction, labels=[False, True])
        positives = int(y_slice.sum())
        negatives = int((~y_slice).sum())
        item: dict[str, object] = {
            "n": int(len(y_slice)),
            "positives": positives,
            "negatives": negatives,
            "prevalence": float(positives / len(y_slice)),
            "default_threshold_0_5": {
                "confusion_matrix_labels_false_true": matrix.astype(int).tolist(),
                "precision": float(precision_score(y_slice, prediction, zero_division=0)),
                "recall": float(recall_score(y_slice, prediction, zero_division=0)),
                "f1": float(f1_score(y_slice, prediction, zero_division=0)),
                "false_positives": int(matrix[0, 1]),
                "false_negatives": int(matrix[1, 0]),
            },
        }
        if positives > 0 and negatives > 0:
            item["average_precision"] = float(average_precision_score(y_slice, probability_slice))
            item["roc_auc"] = float(roc_auc_score(y_slice, probability_slice))
            item["ranking_metrics_status"] = "defined_both_classes_present"
        else:
            item["average_precision"] = None
            item["roc_auc"] = None
            item["ranking_metrics_status"] = "undefined_one_class_slice"
        result[value] = item
    return result


def run(source: Path, membership_path: Path) -> dict[str, object]:
    """Verify the frozen boundary, fit once on train, and score test once."""
    if sha256_file(source) != SOURCE_SHA256:
        raise ValueError("source fingerprint mismatch")
    if sha256_file(membership_path) != MEMBERSHIP_SHA256:
        raise ValueError("membership fingerprint mismatch")
    rows, allowed = load_rows(source)
    if allowed != ALLOWED or TARGET in allowed or "PageValues" in allowed:
        raise ValueError("unexpected feature boundary")
    membership = load_membership(membership_path)
    groups = group_rows(rows, allowed)
    holdout = validate_holdout(rows, groups, membership)
    if holdout["crossing_groups"] or holdout["mixed_target_groups"]:
        raise ValueError("frozen holdout leakage check failed")
    memberships = [(index, row_id(index, row)) for index, row in enumerate(rows)]
    train_fingerprint = fingerprint([item for item in memberships if membership[item[0]] == "train"])
    test_fingerprint = fingerprint([item for item in memberships if membership[item[0]] == "test"])
    if train_fingerprint != TRAIN_FINGERPRINT or test_fingerprint != TEST_FINGERPRINT:
        raise ValueError("frozen split fingerprint mismatch")
    train_indices = [index for index in range(len(rows)) if membership[index] == "train"]
    test_indices = [index for index in range(len(rows)) if membership[index] == "test"]
    if len(train_indices) != 9864 or len(test_indices) != 2466:
        raise ValueError("unexpected frozen split row counts")
    train_rows = [rows[index] for index in train_indices]
    X_train = pd.DataFrame([{column: row[column] for column in ALLOWED} for row in train_rows])
    for column in NUMERIC:
        X_train[column] = pd.to_numeric(X_train[column], errors="raise")
    y_train = np.asarray([row[TARGET] == "TRUE" for row in train_rows], dtype=bool)
    if Counter(y_train) != Counter({False: 8338, True: 1526}):
        raise ValueError("unexpected frozen train class counts")
    model = make_model()
    fit_started = time.perf_counter()
    model.fit(X_train, y_train)
    fit_seconds = time.perf_counter() - fit_started

    # This is the sole test materialization, prediction, and scoring path.
    test_rows = [rows[index] for index in test_indices]
    X_test = pd.DataFrame([{column: row[column] for column in ALLOWED} for row in test_rows])
    for column in NUMERIC:
        X_test[column] = pd.to_numeric(X_test[column], errors="raise")
    y_test = np.asarray([row[TARGET] == "TRUE" for row in test_rows], dtype=bool)
    if Counter(y_test) != Counter({False: 2084, True: 382}):
        raise ValueError("unexpected frozen test class counts")
    probability = model.predict_proba(X_test)[:, 1]
    if not np.isfinite(probability).all():
        raise ValueError("non-finite test probabilities")
    metrics = _binary_metrics(y_test, probability)
    core_values = [metrics[key] for key in ("average_precision", "roc_auc", "balanced_accuracy_default_threshold_0_5", "precision_default_threshold_0_5", "recall_default_threshold_0_5", "f1_default_threshold_0_5")]
    if not all(np.isfinite(value) for value in core_values):
        raise ValueError("non-finite core metric")
    slices = {column: _slice_metrics(X_test[column], y_test, probability) for column in SLICE_COLUMNS}
    return {
        "protocol": {
            "source_sha256": SOURCE_SHA256,
            "membership_sha256": MEMBERSHIP_SHA256,
            "train_fingerprint_sha256": train_fingerprint,
            "test_fingerprint_sha256": test_fingerprint,
            "allowed_features": ALLOWED,
            "excluded_features": ["Revenue", "PageValues"],
            "holdout_validation": holdout,
            "train_rows": len(X_train),
            "test_rows": len(X_test),
            "test_access": "Frozen test materialized once after the single all-train fit; no test-driven change follows.",
        },
        "model": {"class": "sklearn.ensemble.RandomForestClassifier", "params": RF_CONFIG},
        "calibration": {"method": "none", "performed": False},
        "threshold": {"value": DEFAULT_THRESHOLD, "tuned": False, "description": "estimator default decision threshold"},
        "fit_seconds": fit_seconds,
        "test_metrics": metrics,
        "predeclared_slices": list(SLICE_COLUMNS),
        "slices": slices,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--membership", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    started = time.perf_counter()
    result = run(args.source, args.membership)
    result["total_runtime_seconds"] = time.perf_counter() - started
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
