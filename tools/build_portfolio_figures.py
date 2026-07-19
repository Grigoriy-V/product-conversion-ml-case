"""Build portfolio figures from accepted, compact JSON evidence only."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
ASSETS = ROOT / "docs" / "assets"
EXPECTED = {
    "dummy_ap": 0.15470397012817044,
    "logistic_ap": 0.33052640487158447,
    "rf_cv_ap": 0.37908310923231386,
    "rf_holdout_ap": 0.3681482198181665,
}
PALETTE = {"navy": "#0072B2", "orange": "#E69F00", "green": "#009E73", "red": "#D55E00", "gray": "#6C757D"}


def read_json(name: str) -> dict[str, Any]:
    path = REPORTS / name
    if not path.exists():
        raise FileNotFoundError(f"Required accepted evidence is missing: {path}")
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Evidence must be a JSON object: {path}")
    return value


def number(value: Any, key: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        raise ValueError(f"Expected a finite numeric value for {key}, got {value!r}")
    return float(value)


def require(mapping: dict[str, Any], key: str, context: str) -> Any:
    if key not in mapping:
        raise KeyError(f"Missing required key {context}.{key}")
    return mapping[key]


def close_enough(actual: float, expected: float, name: str) -> None:
    if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError(f"Accepted metric mismatch for {name}: {actual} != {expected}")


def load_evidence() -> dict[str, Any]:
    baseline = read_json("online_shoppers_baseline_results.json")
    comparison = read_json("online_shoppers_model_comparison_results.json")
    final = read_json("online_shoppers_final_evaluation_results.json")
    threshold = read_json("online_shoppers_threshold_analysis_results.json")

    baseline_models = require(baseline, "models", "baseline")
    comparison_models = require(comparison, "models", "comparison")
    dummy = number(require(require(require(baseline_models, "dummy_prior", "baseline.models"), "summary", "dummy_prior"), "average_precision", "dummy.summary")["mean"], "dummy AP")
    logistic = number(require(require(require(baseline_models, "logistic_regression", "baseline.models"), "summary", "logistic"), "average_precision", "logistic.summary")["mean"], "logistic AP")
    random_forest = number(require(require(require(comparison_models, "random_forest", "comparison.models"), "summary", "random_forest"), "average_precision", "rf.summary")["mean"], "random forest CV AP")
    final_ap = number(require(require(final, "test_metrics", "final"), "average_precision", "final.test_metrics"), "final holdout AP")
    for name, actual in (("dummy_ap", dummy), ("logistic_ap", logistic), ("rf_cv_ap", random_forest), ("rf_holdout_ap", final_ap)):
        close_enough(actual, EXPECTED[name], name)

    default = require(threshold, "default_threshold_0_5", "threshold")
    points = require(threshold, "recall_constrained_operating_points", "threshold")
    selected = require(threshold, "selected_operating_point", "threshold")
    operating_points = [("Default 0.50", default, "default")]
    for level in ("recall_at_least_0.50", "recall_at_least_0.60", "recall_at_least_0.70"):
        operating_points.append((level.replace("recall_at_least_", "Recall ≥ "), require(points, level, "threshold.points"), "constraint"))
    operating_points.append(("Selected F2", selected, "selected"))
    cleaned = []
    for label, point, kind in operating_points:
        if not isinstance(point, dict):
            raise ValueError(f"Operating point {label} must be an object")
        cleaned.append({
            "label": label,
            "kind": kind,
            "threshold": number(require(point, "threshold", label), f"{label}.threshold"),
            "precision": number(require(point, "precision", label), f"{label}.precision"),
            "recall": number(require(point, "recall", label), f"{label}.recall"),
            "predicted_positive_rate": number(require(point, "predicted_positive_rate", label), f"{label}.predicted_positive_rate"),
        })
    return {"aps": (dummy, logistic, random_forest, final_ap), "operating_points": cleaned}


def save_all(fig: plt.Figure, stem: str) -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    fig.savefig(ASSETS / f"{stem}.png", dpi=180, bbox_inches="tight", facecolor="white")
    fig.savefig(ASSETS / f"{stem}.svg", bbox_inches="tight", facecolor="white", metadata={"Date": None})
    plt.close(fig)


def build_ap_comparison(aps: tuple[float, float, float, float]) -> None:
    labels = ["Dummy prior\n(train CV)", "Logistic regression\n(train CV)", "Random forest\n(train CV)", "Random forest\n(final holdout)"]
    colors = [PALETTE["gray"], PALETTE["navy"], PALETTE["green"], PALETTE["orange"]]
    fig, ax = plt.subplots(figsize=(10.5, 5.8), constrained_layout=True)
    bars = ax.bar(labels, aps, color=colors, width=0.68)
    ax.set_title("Average precision: accepted model evidence", loc="left", weight="bold", pad=14)
    ax.set_ylabel("Average precision (higher is better)")
    ax.set_ylim(0, 0.46)
    ax.grid(axis="y", color="#D9D9D9", linewidth=0.8)
    ax.set_axisbelow(True)
    for bar, value in zip(bars, aps, strict=True):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.012, f"{value:.3f}", ha="center", va="bottom", weight="bold")
    ax.text(0.01, -0.22, "Train-CV values are five-fold group-safe means. The final holdout was scored once after selection.", transform=ax.transAxes, fontsize=9, color="#404040")
    save_all(fig, "model_ap_comparison")


def build_threshold_tradeoff(points: list[dict[str, Any]]) -> None:
    fig, ax = plt.subplots(figsize=(9.6, 6.6), constrained_layout=True)
    for point in points:
        style = {"default": (PALETTE["red"], "X", 125), "constraint": (PALETTE["navy"], "o", 80), "selected": (PALETTE["orange"], "*", 230)}[point["kind"]]
        color, marker, size = style
        ax.scatter(point["recall"], point["precision"], color=color, marker=marker, s=size, zorder=3, label=point["label"])
        label = f"t={point['threshold']:.3f}\npositive={point['predicted_positive_rate']:.1%}"
        offset = (9, 7) if point["kind"] != "default" else (9, -30)
        ax.annotate(label, (point["recall"], point["precision"]), xytext=offset, textcoords="offset points", fontsize=8.5, color="#303030")
    ax.set_title("Threshold trade-off on train-only OOF predictions", loc="left", weight="bold", pad=14)
    ax.set_xlabel("Recall (higher finds more conversions)")
    ax.set_ylabel("Precision (higher means fewer false alerts)")
    ax.set_xlim(0, 1.0)
    ax.set_ylim(0, 0.68)
    ax.grid(color="#D9D9D9", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="upper right")
    ax.text(0.01, -0.18, "Points are preselected operating points, not a continuous precision–recall curve. No frozen-test data were used for threshold selection.", transform=ax.transAxes, fontsize=8.7, color="#404040")
    save_all(fig, "threshold_tradeoff")


def main() -> None:
    evidence = load_evidence()
    build_ap_comparison(evidence["aps"])
    build_threshold_tradeoff(evidence["operating_points"])
    print("Built docs/assets/model_ap_comparison.{png,svg} and docs/assets/threshold_tradeoff.{png,svg}")


if __name__ == "__main__":
    main()
