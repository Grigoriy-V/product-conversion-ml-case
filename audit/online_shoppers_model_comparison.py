"""Fixed train-only comparison for the Online Shoppers step-5 candidate."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

try:
    from audit.online_shoppers_baseline import (
        N_FOLDS, load_train_only, make_preprocessor, score_model, summarize,
        validate_folds,
    )
except ModuleNotFoundError:
    from online_shoppers_baseline import (  # type: ignore[no-redef]
        N_FOLDS, load_train_only, make_preprocessor, score_model, summarize,
        validate_folds,
    )


RF_CONFIG = {
    "n_estimators": 200,
    "random_state": 20260719,
    "n_jobs": -1,
    "min_samples_leaf": 2,
}
ACCEPTED_LOGISTIC_AP = 0.33052640487158447
RF_AP_IMPROVEMENT_REQUIRED = 0.01


def make_models() -> dict[str, Pipeline]:
    """Return the two predeclared, untuned fold-fitted pipelines."""
    return {
        "logistic_regression": Pipeline([
            ("preprocess", make_preprocessor()),
            ("model", LogisticRegression(max_iter=1000, solver="lbfgs")),
        ]),
        "random_forest": Pipeline([
            ("preprocess", make_preprocessor()),
            ("model", RandomForestClassifier(**RF_CONFIG)),
        ]),
    }


def run(source: Path, membership: Path) -> dict[str, object]:
    X, y, folds, boundary = load_train_only(source, membership)
    fold_checks = validate_folds(y, folds)
    results: dict[str, object] = {}
    for name, model in make_models().items():
        per_fold, runtime_seconds = score_model(model, X, y, folds)
        if not all(np.isfinite(value) for item in per_fold for key, value in item.items() if key != "fold"):
            raise ValueError(f"non-finite metric from {name}")
        results[name] = {
            "per_fold": per_fold,
            "summary": summarize(per_fold),
            "runtime_seconds": runtime_seconds,
        }
    rf_ap = results["random_forest"]["summary"]["average_precision"]["mean"]  # type: ignore[index]
    selected = "random_forest" if rf_ap >= ACCEPTED_LOGISTIC_AP + RF_AP_IMPROVEMENT_REQUIRED else "logistic_regression"
    return {
        "protocol": {
            **boundary,
            **fold_checks,
            "n_folds": N_FOLDS,
            "test_access": "No held-out test row enters X, y, fit, predict, or scoring.",
        },
        "models": results,
        "selection": {
            "accepted_logistic_average_precision": ACCEPTED_LOGISTIC_AP,
            "random_forest_absolute_improvement_required": RF_AP_IMPROVEMENT_REQUIRED,
            "selected_model": selected,
            "rule": "Select Random Forest only when mean AP is at least accepted logistic AP plus 0.01; otherwise retain Logistic Regression for simplicity.",
        },
        "random_forest_config": RF_CONFIG,
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
