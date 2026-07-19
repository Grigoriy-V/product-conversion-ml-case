"""No-model validation utilities for the accepted Online Shoppers feature boundary."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


SEED = 20260719
N_FOLDS = 5
TARGET = "Revenue"
PROHIBITED = {"Revenue", "PageValues"}


def feature_group_id(row: dict[str, str], allowed_features: list[str]) -> str:
    payload = json.dumps(
        [row[column] for column in allowed_features], separators=(",", ":")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_rows(source: Path) -> tuple[list[dict[str, str]], list[str]]:
    with source.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        if reader.fieldnames is None:
            raise ValueError("source has no header")
    allowed = [column for column in reader.fieldnames if column not in PROHIBITED]
    if TARGET in allowed or "PageValues" in allowed:
        raise ValueError("prohibited columns entered the model-feature boundary")
    return rows, allowed


def load_membership(membership: Path) -> dict[int, str]:
    with membership.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        result = {int(row["source_row_index"]): row["split"] for row in reader}
    if set(result.values()) != {"train", "test"}:
        raise ValueError("membership must contain train and test rows")
    return result


def group_rows(rows: list[dict[str, str]], allowed_features: list[str]) -> dict[str, list[int]]:
    groups: dict[str, list[int]] = defaultdict(list)
    for index, row in enumerate(rows):
        groups[feature_group_id(row, allowed_features)].append(index)
    return dict(groups)


def validate_holdout(
    rows: list[dict[str, str]], groups: dict[str, list[int]], membership: dict[int, str]
) -> dict[str, object]:
    if set(membership) != set(range(len(rows))):
        raise ValueError("membership does not cover each source row exactly once")
    crossing = [group_id for group_id, indices in groups.items() if len({membership[index] for index in indices}) > 1]
    mixed = [group_id for group_id, indices in groups.items() if len({rows[index][TARGET] for index in indices}) > 1]
    return {
        "groups": len(groups),
        "crossing_groups": len(crossing),
        "crossing_rows": sum(len(groups[group_id]) for group_id in crossing),
        "mixed_target_groups": len(mixed),
        "mixed_target_rows": sum(len(groups[group_id]) for group_id in mixed),
        "split_class_counts": {
            split: dict(sorted(Counter(rows[index][TARGET] for index, value in membership.items() if value == split).items()))
            for split in ("train", "test")
        },
    }


def deterministic_training_folds(
    rows: list[dict[str, str]], groups: dict[str, list[int]], membership: dict[int, str]
) -> dict[int, int]:
    """Assign whole, target-pure training groups to five deterministic folds."""
    train_groups: dict[str, list[int]] = {
        group_id: indices for group_id, indices in groups.items() if membership[indices[0]] == "train"
    }
    if any(any(membership[index] != "train" for index in indices) for indices in train_groups.values()):
        raise ValueError("a model-feature group crosses the frozen holdout")
    by_label: dict[str, list[tuple[str, list[int]]]] = defaultdict(list)
    for group_id, indices in train_groups.items():
        labels = {rows[index][TARGET] for index in indices}
        if len(labels) != 1:
            raise ValueError("cannot stratify a mixed-target model-feature group")
        by_label[labels.pop()].append((group_id, indices))

    fold_rows = [0] * N_FOLDS
    fold_label_rows: list[Counter[str]] = [Counter() for _ in range(N_FOLDS)]
    assignment: dict[int, int] = {}
    for label in sorted(by_label):
        ordered = sorted(
            by_label[label],
            key=lambda item: (-len(item[1]), hashlib.sha256(f"{SEED}|{label}|{item[0]}".encode()).hexdigest()),
        )
        for group_id, indices in ordered:
            fold = min(
                range(N_FOLDS),
                key=lambda candidate: (
                    fold_label_rows[candidate][label],
                    fold_rows[candidate],
                    hashlib.sha256(f"{SEED}|{label}|{group_id}|{candidate}".encode()).hexdigest(),
                ),
            )
            for index in indices:
                assignment[index] = fold
            fold_rows[fold] += len(indices)
            fold_label_rows[fold][label] += len(indices)
    return assignment


def fold_summary(rows: list[dict[str, str]], assignment: dict[int, int]) -> dict[int, dict[str, int]]:
    return {
        fold: dict(sorted(Counter(rows[index][TARGET] for index, value in assignment.items() if value == fold).items()))
        for fold in range(N_FOLDS)
    }
