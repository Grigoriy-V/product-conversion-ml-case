"""Reproducible no-model audit and frozen split for UCI Online Shoppers data."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import random
import sys
from collections import Counter
from pathlib import Path

EXPECTED_COLUMNS = [
    "Administrative", "Administrative_Duration", "Informational",
    "Informational_Duration", "ProductRelated", "ProductRelated_Duration",
    "BounceRates", "ExitRates", "PageValues", "SpecialDay", "Month",
    "OperatingSystems", "Browser", "Region", "TrafficType", "VisitorType",
    "Weekend", "Revenue",
]
NUMERIC_FEATURES = [
    "Administrative", "Administrative_Duration", "Informational",
    "Informational_Duration", "ProductRelated", "ProductRelated_Duration",
    "BounceRates", "ExitRates", "SpecialDay",
]
CATEGORICAL_FEATURES = ["Month", "OperatingSystems", "Browser", "Region", "TrafficType", "VisitorType", "Weekend"]
EXCLUDED_FEATURES = {"PageValues": "post-outcome Google Analytics metric"}
SEED = 20260719
TEST_FRACTION = 0.20


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def row_id(index: int, row: dict[str, str]) -> str:
    payload = json.dumps([index, [row[column] for column in EXPECTED_COLUMNS]],
                         ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def fingerprint(items: list[tuple[int, str]]) -> str:
    canonical = "\n".join(f"{index},{digest}" for index, digest in sorted(items)) + "\n"
    return hashlib.sha256(canonical.encode("ascii")).hexdigest()


def feature_group_id(row: dict[str, str]) -> str:
    payload = json.dumps([row[column] for column in EXPECTED_COLUMNS if column != "Revenue"],
                         ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def exact_group_subset(groups: list[tuple[str, list[int]]], target: int) -> set[str]:
    """Choose shuffled whole groups summing exactly to target; no group crosses split."""
    reachable: dict[int, list[str]] = {0: []}
    for group_id, indices in groups:
        size = len(indices)
        for previous in sorted(list(reachable), reverse=True):
            candidate = previous + size
            if candidate <= target and candidate not in reachable:
                reachable[candidate] = reachable[previous] + [group_id]
        if target in reachable:
            break
    if target not in reachable:
        raise ValueError(f"Cannot allocate whole groups to target count {target}")
    return set(reachable[target])


def audit_and_split(source: Path, report_path: Path, split_path: Path) -> dict:
    with source.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != EXPECTED_COLUMNS:
            raise ValueError(f"Unexpected schema: {reader.fieldnames!r}")
        rows = list(reader)
    if any(set(row) != set(EXPECTED_COLUMNS) for row in rows):
        raise ValueError("A row does not match the expected schema")
    missing = {column: sum(not row[column].strip() for row in rows) for column in EXPECTED_COLUMNS}
    duplicate_rows = len(rows) - len({tuple(row[column] for column in EXPECTED_COLUMNS) for row in rows})
    target = Counter(row["Revenue"] for row in rows)
    if set(target) != {"FALSE", "TRUE"}:
        raise ValueError(f"Unexpected Revenue values: {sorted(target)}")

    # Deterministic stratified random holdout. It uses no fitted transformer/model.
    groups_by_label: dict[str, dict[str, list[int]]] = {label: {} for label in target}
    for index, row in enumerate(rows):
        group_id = feature_group_id(row)
        groups_by_label[row["Revenue"]].setdefault(group_id, []).append(index)
    mixed_label_groups = set(groups_by_label["FALSE"]) & set(groups_by_label["TRUE"])
    if mixed_label_groups:
        raise ValueError("Feature-identical groups have conflicting targets")
    rng = random.Random(SEED)
    test_indices: set[int] = set()
    class_counts: dict[str, dict[str, int]] = {}
    for label in sorted(target):
        groups = list(groups_by_label[label].items())
        rng.shuffle(groups)
        total = sum(len(indices) for _, indices in groups)
        n_test = round(total * TEST_FRACTION)
        selected = exact_group_subset(groups, n_test)
        test_indices.update(index for group_id, indices in groups if group_id in selected for index in indices)
        class_counts[label] = {"total": total, "test": n_test, "train": total - n_test}
    memberships = [(index, row_id(index, row)) for index, row in enumerate(rows)]
    train = [item for item in memberships if item[0] not in test_indices]
    test = [item for item in memberships if item[0] in test_indices]

    split_path.parent.mkdir(parents=True, exist_ok=True)
    with split_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["split", "source_row_index", "row_sha256"])
        for index, digest in sorted(train): writer.writerow(["train", index, digest])
        for index, digest in sorted(test): writer.writerow(["test", index, digest])

    report = {
        "dataset": {"name": "UCI Online Shoppers Purchasing Intention Dataset", "uci_id": 468,
                    "source_url": "https://archive.ics.uci.edu/static/public/468/online+shoppers+purchasing+intention+dataset.zip",
                    "documentation_url": "https://archive.ics.uci.edu/dataset/468/online+shoppers+purchasing+intention+dataset",
                    "license": "CC BY 4.0", "file": source.name,
                    "sha256": sha256_file(source)},
        "shape": {"rows": len(rows), "column_count": len(EXPECTED_COLUMNS), "columns": EXPECTED_COLUMNS},
        "storage_types": {"csv": "all fields are strings on disk; semantic roles below"},
        "semantic_types": {"integer": ["Administrative", "Informational", "ProductRelated", "OperatingSystems", "Browser", "Region", "TrafficType"],
                           "continuous": ["Administrative_Duration", "Informational_Duration", "ProductRelated_Duration", "BounceRates", "ExitRates", "PageValues", "SpecialDay"],
                           "categorical": ["Month", "VisitorType", "Weekend", "Revenue"]},
        "missing_values": missing, "exact_duplicate_rows": duplicate_rows,
        "target": {"column": "Revenue", "values": dict(sorted(target.items())),
                   "positive_class": "TRUE", "positive_rate": target["TRUE"] / len(rows)},
        "features": {"included_numeric": NUMERIC_FEATURES, "included_categorical": CATEGORICAL_FEATURES,
                     "excluded": EXCLUDED_FEATURES, "prohibited": ["Revenue", "PageValues"]},
        "split": {"strategy": "random", "algorithm": "Python random.Random; independently shuffle target-pure groups of identical non-target features in sorted label order; choose whole groups summing to round(class_count * 0.20) for test",
                  "seed": SEED, "test_fraction": TEST_FRACTION, "stratified_by": "Revenue",
                  "train_rows": len(train), "test_rows": len(test), "class_counts": class_counts,
                  "feature_identical_groups": len({feature_group_id(row) for row in rows}), "mixed_target_groups": len(mixed_label_groups),
                  "train_fingerprint_sha256": fingerprint(train), "test_fingerprint_sha256": fingerprint(test),
                  "membership_path": str(split_path).replace("\\", "/")},
        "runtime": {"python_version": platform.python_version(), "executor": "audit/online_shoppers_audit.py"},
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--split", type=Path, required=True)
    args = parser.parse_args()
    report = audit_and_split(args.source, args.report, args.split)
    print(json.dumps({"sha256": report["dataset"]["sha256"], "rows": report["shape"]["rows"], "split": report["split"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
