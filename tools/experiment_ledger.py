"""Append-only audit ledger for the classical-ML adapter.

The helper enforces the documented ``bundled-classical-v2`` contract. It does
not implement or claim a complete JSON Schema draft. Callers provide event
evidence only; UUIDv4 identifiers and exact system UTC timestamps are generated
inside the append operation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import re
import socket
import stat
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "reports" / "experiment_ledger.jsonl"
SCHEMA_VERSION = "2.0"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
EVENT_ID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
TIMESTAMP_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T"
    r"[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z$"
)
EXPERIMENT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,127}$")
CLASS_RE = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+$"
)
REPARSE_POINT = 0x400

OPERATIONS = ("dataset_audit", "baseline", "evaluation", "closeout")
STATUSES = ("completed", "failed", "skipped", "pending")
OPERATION_RANK = {name: index for index, name in enumerate(OPERATIONS)}
FULL_KEYS = {
    "schema_version",
    "event_id",
    "timestamp_utc",
    "experiment_id",
    "operation",
    "status",
    "commands",
    "runtime",
    "dataset",
    "leakage_audit",
    "split",
    "features",
    "pipeline",
    "baseline_cv",
    "calibration",
    "threshold",
    "artifacts",
    "decision",
}
CALLER_KEYS = FULL_KEYS - {"event_id", "timestamp_utc"}


class LedgerError(ValueError):
    """The ledger contract or append lifecycle is invalid."""


# Compatibility for callers/tests that used the v1 name.
Error = LedgerError


def system_utc() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _closed_object(value: Any, keys: set[str], name: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise LedgerError(f"{name} must be a closed object with fields {sorted(keys)}")
    return value


def _nonempty_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LedgerError(f"{name} must be a non-empty string")
    if value.strip().lower() in {"unknown", "pending", "placeholder", "n/a", "none"}:
        raise LedgerError(f"{name} must not be a placeholder")
    return value


def _string_array(
    value: Any, name: str, *, nonempty: bool = False
) -> list[str]:
    if not isinstance(value, list):
        raise LedgerError(f"{name} must be an array")
    if nonempty and not value:
        raise LedgerError(f"{name} must not be empty")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise LedgerError(f"{name} entries must be non-empty strings")
    if len(value) != len(set(value)):
        raise LedgerError(f"{name} entries must be unique")
    return value


def _finite_number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise LedgerError(f"{name} must be numeric")
    if not math.isfinite(float(value)):
        raise LedgerError(f"{name} must be finite")
    return float(value)


def _json_value(value: Any, name: str) -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise LedgerError(f"{name} contains a non-finite number")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _json_value(item, f"{name}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str) or not key:
                raise LedgerError(f"{name} contains an invalid key")
            _json_value(item, f"{name}.{key}")
        return
    raise LedgerError(f"{name} contains a non-JSON value")


def _timestamp(value: Any) -> datetime:
    if not isinstance(value, str) or not TIMESTAMP_RE.fullmatch(value):
        raise LedgerError("timestamp_utc must be an exact UTC timestamp ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise LedgerError("timestamp_utc is not a real calendar timestamp") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise LedgerError("timestamp_utc must be UTC")
    return parsed


def _runtime(value: Any) -> dict[str, Any]:
    runtime = _closed_object(
        value,
        {"python_version", "platform", "executor", "packages"},
        "runtime",
    )
    _nonempty_string(runtime["python_version"], "runtime.python_version")
    _nonempty_string(runtime["platform"], "runtime.platform")
    _nonempty_string(runtime["executor"], "runtime.executor")
    packages = runtime["packages"]
    if not isinstance(packages, dict) or not packages:
        raise LedgerError("runtime.packages must be a non-empty object")
    for package, version in packages.items():
        _nonempty_string(package, "runtime package name")
        _nonempty_string(version, f"runtime.packages.{package}")
    return runtime


def _dataset(value: Any) -> dict[str, Any]:
    dataset = _closed_object(
        value,
        {"name", "source", "license", "fingerprint_sha256", "target"},
        "dataset",
    )
    _nonempty_string(dataset["name"], "dataset.name")
    _nonempty_string(dataset["source"], "dataset.source")
    _nonempty_string(dataset["license"], "dataset.license")
    if not isinstance(dataset["fingerprint_sha256"], str) or not SHA256_RE.fullmatch(
        dataset["fingerprint_sha256"]
    ):
        raise LedgerError("dataset.fingerprint_sha256 must be lowercase SHA-256")
    target = _closed_object(
        dataset["target"],
        {"column", "task_type", "positive_class"},
        "dataset.target",
    )
    _nonempty_string(target["column"], "dataset.target.column")
    if target["task_type"] != "binary_classification":
        raise LedgerError("dataset.target.task_type must be binary_classification")
    positive = target["positive_class"]
    if isinstance(positive, bool) or not isinstance(positive, (str, int)):
        raise LedgerError("dataset.target.positive_class must be a string or integer")
    if isinstance(positive, str):
        _nonempty_string(positive, "dataset.target.positive_class")
    return dataset


def _leakage(value: Any, target_column: str) -> dict[str, Any]:
    audit = _closed_object(
        value,
        {"checked", "methods", "findings", "prohibited_features"},
        "leakage_audit",
    )
    if audit["checked"] is not True:
        raise LedgerError("leakage_audit.checked must be true")
    _string_array(audit["methods"], "leakage_audit.methods", nonempty=True)
    _string_array(audit["findings"], "leakage_audit.findings")
    prohibited = _string_array(
        audit["prohibited_features"],
        "leakage_audit.prohibited_features",
        nonempty=True,
    )
    if target_column not in prohibited:
        raise LedgerError("target column must be prohibited as a model feature")
    return audit


def _split(value: Any, target_column: str) -> dict[str, Any]:
    split = _closed_object(
        value,
        {
            "strategy",
            "random_state",
            "stratified",
            "stratify_by",
            "train_fingerprint_sha256",
            "test_fingerprint_sha256",
        },
        "split",
    )
    if split["strategy"] not in {"random", "temporal", "group"}:
        raise LedgerError("split.strategy is unsupported")
    random_state = split["random_state"]
    if split["strategy"] == "random":
        if isinstance(random_state, bool) or not isinstance(random_state, int):
            raise LedgerError("random split requires an integer random_state")
    elif random_state is not None:
        raise LedgerError("non-random split requires random_state null")
    if not isinstance(split["stratified"], bool):
        raise LedgerError("split.stratified must be boolean")
    if split["stratified"]:
        if split["stratify_by"] != target_column:
            raise LedgerError("stratified split must use the target column")
    elif split["stratify_by"] is not None:
        raise LedgerError("non-stratified split requires stratify_by null")
    fingerprints = (
        split["train_fingerprint_sha256"],
        split["test_fingerprint_sha256"],
    )
    if any(not isinstance(item, str) or not SHA256_RE.fullmatch(item) for item in fingerprints):
        raise LedgerError("split fingerprints must be lowercase SHA-256")
    if fingerprints[0] == fingerprints[1]:
        raise LedgerError("train and test fingerprints must differ")
    return split


def _features(value: Any, target_column: str) -> dict[str, Any]:
    features = _closed_object(
        value,
        {"included", "categorical", "numeric", "excluded"},
        "features",
    )
    included = _string_array(features["included"], "features.included", nonempty=True)
    categorical = _string_array(features["categorical"], "features.categorical")
    numeric = _string_array(features["numeric"], "features.numeric")
    excluded = _string_array(features["excluded"], "features.excluded", nonempty=True)
    if set(categorical) & set(numeric):
        raise LedgerError("categorical and numeric features must be disjoint")
    if set(categorical) | set(numeric) != set(included):
        raise LedgerError("categorical and numeric features must partition included")
    if target_column in included or target_column not in excluded:
        raise LedgerError("target must be excluded from model features")
    return features


def _model(value: Any, name: str) -> dict[str, Any]:
    model = _closed_object(value, {"class", "params"}, name)
    if not isinstance(model["class"], str) or not CLASS_RE.fullmatch(model["class"]):
        raise LedgerError(f"{name}.class must be a fully-qualified class")
    if not isinstance(model["params"], dict) or not model["params"]:
        raise LedgerError(f"{name}.params must be a non-empty object")
    _json_value(model["params"], f"{name}.params")
    return model


def _pipeline(value: Any) -> dict[str, Any]:
    pipeline = _closed_object(value, {"library", "class", "steps"}, "pipeline")
    if pipeline["library"] != "sklearn":
        raise LedgerError("pipeline.library must be sklearn")
    if pipeline["class"] != "sklearn.pipeline.Pipeline":
        raise LedgerError("pipeline.class must be sklearn.pipeline.Pipeline")
    steps = pipeline["steps"]
    if not isinstance(steps, list) or len(steps) < 2:
        raise LedgerError("pipeline.steps must contain preprocessing and estimator")
    names: set[str] = set()
    for index, step in enumerate(steps):
        step = _closed_object(step, {"name", "class", "params"}, f"pipeline.steps[{index}]")
        name = _nonempty_string(step["name"], f"pipeline.steps[{index}].name")
        if name in names:
            raise LedgerError("pipeline step names must be unique")
        names.add(name)
        if not isinstance(step["class"], str) or not CLASS_RE.fullmatch(step["class"]):
            raise LedgerError("pipeline step classes must be fully qualified")
        if not isinstance(step["params"], dict) or not step["params"]:
            raise LedgerError("pipeline step params must be non-empty objects")
        _json_value(step["params"], f"pipeline.steps[{index}].params")
    return pipeline


def _metrics(value: Any, name: str) -> dict[str, float]:
    if not isinstance(value, dict) or not value:
        raise LedgerError(f"{name} must be a non-empty metric object")
    result: dict[str, float] = {}
    for metric, score in value.items():
        _nonempty_string(metric, f"{name} metric")
        result[metric] = _finite_number(score, f"{name}.{metric}")
    return result


def _baseline_cv(value: Any, pipeline: dict[str, Any]) -> dict[str, Any]:
    evidence = _closed_object(
        value,
        {"baseline_model", "cv", "metrics", "primary_metric"},
        "baseline_cv",
    )
    model = _model(evidence["baseline_model"], "baseline_cv.baseline_model")
    if model["class"] != pipeline["steps"][-1]["class"]:
        raise LedgerError("baseline model must match the final Pipeline estimator")
    cv = _closed_object(
        evidence["cv"],
        {"strategy", "folds", "shuffle", "random_state"},
        "baseline_cv.cv",
    )
    if cv["strategy"] not in {
        "StratifiedKFold",
        "GroupKFold",
        "TimeSeriesSplit",
    }:
        raise LedgerError("baseline_cv.cv.strategy is unsupported")
    if isinstance(cv["folds"], bool) or not isinstance(cv["folds"], int) or not 2 <= cv["folds"] <= 20:
        raise LedgerError("baseline_cv.cv.folds must be an integer from 2 to 20")
    if not isinstance(cv["shuffle"], bool):
        raise LedgerError("baseline_cv.cv.shuffle must be boolean")
    if cv["shuffle"]:
        if isinstance(cv["random_state"], bool) or not isinstance(cv["random_state"], int):
            raise LedgerError("shuffled CV requires an integer random_state")
    elif cv["random_state"] is not None:
        raise LedgerError("unshuffled CV requires random_state null")
    if cv["strategy"] in {"GroupKFold", "TimeSeriesSplit"} and cv["shuffle"]:
        raise LedgerError("GroupKFold and TimeSeriesSplit cannot shuffle")
    metrics = _metrics(evidence["metrics"], "baseline_cv.metrics")
    if evidence["primary_metric"] not in metrics:
        raise LedgerError("baseline_cv.primary_metric must name a recorded metric")
    return evidence


def _calibration(value: Any) -> dict[str, Any]:
    calibration = _closed_object(
        value,
        {"method", "cv_folds", "metrics_before", "metrics_after"},
        "calibration",
    )
    if calibration["method"] not in {"sigmoid", "isotonic", "none"}:
        raise LedgerError("calibration.method is unsupported")
    if (
        isinstance(calibration["cv_folds"], bool)
        or not isinstance(calibration["cv_folds"], int)
        or not 2 <= calibration["cv_folds"] <= 20
    ):
        raise LedgerError("calibration.cv_folds must be an integer from 2 to 20")
    _metrics(calibration["metrics_before"], "calibration.metrics_before")
    _metrics(calibration["metrics_after"], "calibration.metrics_after")
    return calibration


def _threshold(value: Any) -> dict[str, Any]:
    threshold = _closed_object(
        value,
        {
            "value",
            "objective",
            "selection_split",
            "metric_name",
            "metric_value",
        },
        "threshold",
    )
    number = _finite_number(threshold["value"], "threshold.value")
    if not 0 <= number <= 1:
        raise LedgerError("threshold.value must be between 0 and 1")
    _nonempty_string(threshold["objective"], "threshold.objective")
    if threshold["selection_split"] not in {"validation", "train_cv_oof"}:
        raise LedgerError("threshold.selection_split is unsupported")
    _nonempty_string(threshold["metric_name"], "threshold.metric_name")
    _finite_number(threshold["metric_value"], "threshold.metric_value")
    return threshold


def _is_reparse(path: Path) -> bool:
    info = path.lstat()
    return path.is_symlink() or bool(
        getattr(info, "st_file_attributes", 0) & REPARSE_POINT
    )


def _portable_relative(value: Any, name: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise LedgerError(f"{name} must be a non-empty relative path")
    if "\\" in value or ":" in value:
        raise LedgerError(f"{name} must use portable repository-relative POSIX syntax")
    relative = PurePosixPath(value)
    if (
        relative.is_absolute()
        or value != relative.as_posix()
        or any(part in {"", ".", ".."} for part in relative.parts)
    ):
        raise LedgerError(f"unsafe {name}: {value!r}")
    return relative


def _regular_file(root: Path, value: str, name: str) -> Path:
    relative = _portable_relative(value, name)
    root = root.absolute()
    if not root.is_dir() or _is_reparse(root):
        raise LedgerError("project root is missing or is a link/reparse point")
    current = root
    for part in relative.parts:
        current = current / part
        try:
            if _is_reparse(current):
                raise LedgerError(f"{name} traverses a link/reparse point")
        except FileNotFoundError as exc:
            raise LedgerError(f"{name} is missing: {value}") from exc
    try:
        resolved_root = root.resolve(strict=True)
        resolved = current.resolve(strict=True)
        resolved.relative_to(resolved_root)
    except (OSError, ValueError) as exc:
        raise LedgerError(f"{name} escapes the project root") from exc
    if not stat.S_ISREG(resolved.stat().st_mode):
        raise LedgerError(f"{name} must be a regular file")
    return resolved


def _artifacts(value: Any, root: Path) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise LedgerError("artifacts must be an array")
    seen: set[str] = set()
    for index, artifact in enumerate(value):
        artifact = _closed_object(
            artifact, {"path", "sha256"}, f"artifacts[{index}]"
        )
        path = artifact["path"]
        if path in seen:
            raise LedgerError("artifact paths must be unique")
        seen.add(path)
        if not isinstance(artifact["sha256"], str) or not SHA256_RE.fullmatch(
            artifact["sha256"]
        ):
            raise LedgerError("artifact SHA-256 must be lowercase hexadecimal")
        artifact_file = _regular_file(root, path, f"artifacts[{index}].path")
        if sha256_file(artifact_file) != artifact["sha256"]:
            raise LedgerError(f"artifact hash mismatch: {path}")
    return value


def _decision(value: Any, status: str) -> dict[str, str]:
    decision = _closed_object(value, {"action", "rationale"}, "decision")
    actions = {
        "completed": {"continue", "stop", "change", "freeze"},
        "failed": {"stop", "change"},
        "skipped": {"stop", "change"},
        "pending": {"pending"},
    }
    if decision["action"] not in actions[status]:
        raise LedgerError(f"decision.action is invalid for status {status}")
    _nonempty_string(decision["rationale"], "decision.rationale")
    return decision


def validate_event(event: Any, *, root: Path = ROOT) -> dict[str, Any]:
    """Validate one complete stored event, including referenced artifacts."""

    event = _closed_object(event, FULL_KEYS, "event")
    if event["schema_version"] != SCHEMA_VERSION:
        raise LedgerError(f"schema_version must be {SCHEMA_VERSION}")
    if not isinstance(event["event_id"], str) or not EVENT_ID_RE.fullmatch(
        event["event_id"]
    ):
        raise LedgerError("event_id must be a canonical UUIDv4")
    _timestamp(event["timestamp_utc"])
    if not isinstance(event["experiment_id"], str) or not EXPERIMENT_ID_RE.fullmatch(
        event["experiment_id"]
    ):
        raise LedgerError("experiment_id has an invalid stable identifier")
    if event["operation"] not in OPERATIONS:
        raise LedgerError("operation is unsupported")
    if event["status"] not in STATUSES:
        raise LedgerError("status is unsupported")
    commands = _string_array(event["commands"], "commands")
    status = event["status"]
    operation = event["operation"]
    _decision(event["decision"], status)
    _artifacts(event["artifacts"], root)

    if status != "completed":
        if status == "failed":
            if not commands:
                raise LedgerError("failed event must record the command that failed")
            _runtime(event["runtime"])
        elif commands or event["runtime"] is not None:
            raise LedgerError("pending/skipped events cannot claim commands or runtime")
        for field in (
            "dataset",
            "leakage_audit",
            "split",
            "features",
            "pipeline",
            "baseline_cv",
            "calibration",
            "threshold",
        ):
            if event[field] is not None:
                raise LedgerError(
                    f"{status} event cannot fabricate result field {field}"
                )
        if event["artifacts"]:
            raise LedgerError(f"{status} event cannot claim result artifacts")
        return event

    if not commands:
        raise LedgerError("completed event must record at least one exact command")
    _runtime(event["runtime"])
    dataset = _dataset(event["dataset"])
    target_column = dataset["target"]["column"]
    relevant: set[str]
    if operation == "dataset_audit":
        _leakage(event["leakage_audit"], target_column)
        _split(event["split"], target_column)
        _features(event["features"], target_column)
        relevant = {"leakage_audit", "split", "features"}
    elif operation == "baseline":
        pipeline = _pipeline(event["pipeline"])
        _baseline_cv(event["baseline_cv"], pipeline)
        relevant = {"pipeline", "baseline_cv"}
    elif operation == "evaluation":
        pipeline = _pipeline(event["pipeline"])
        _baseline_cv(event["baseline_cv"], pipeline)
        _calibration(event["calibration"])
        _threshold(event["threshold"])
        relevant = {"pipeline", "baseline_cv", "calibration", "threshold"}
    else:
        relevant = set()
    for field in {
        "leakage_audit",
        "split",
        "features",
        "pipeline",
        "baseline_cv",
        "calibration",
        "threshold",
    } - relevant:
        if event[field] is not None:
            raise LedgerError(
                f"{operation} completed event cannot claim irrelevant field {field}"
            )
    return event


def _parse_json(text: str, context: str) -> Any:
    def reject_constant(value: str) -> None:
        raise LedgerError(f"{context} contains invalid JSON constant {value}")

    try:
        return json.loads(text, parse_constant=reject_constant)
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise LedgerError(f"{context} is not valid strict JSON: {exc}") from exc


def read_events(path: Path, *, root: Path = ROOT) -> list[dict[str, Any]]:
    """Read and validate every immutable JSONL record."""

    if not path.exists():
        return []
    try:
        raw = path.read_bytes()
        text = raw.decode("utf-8")
    except (OSError, UnicodeError) as exc:
        raise LedgerError(f"cannot read ledger: {exc}") from exc
    if not raw:
        return []
    if not raw.endswith(b"\n"):
        raise LedgerError("ledger must end with a newline")
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line:
            raise LedgerError(f"blank ledger line {line_number}")
        event = _parse_json(line, f"ledger line {line_number}")
        try:
            validate_event(event, root=root)
        except LedgerError as exc:
            raise LedgerError(f"ledger line {line_number}: {exc}") from exc
        events.append(event)
    validate_sequence(events)
    return events


def validate_sequence(events: list[dict[str, Any]]) -> None:
    """Validate uniqueness, timestamp order, identity, and stage lifecycle."""

    ids: set[str] = set()
    previous_time: datetime | None = None
    state: dict[str, dict[str, Any]] = {}
    for index, event in enumerate(events, 1):
        if event["event_id"] in ids:
            raise LedgerError(f"duplicate event_id at record {index}")
        ids.add(event["event_id"])
        current_time = _timestamp(event["timestamp_utc"])
        if previous_time is not None and current_time <= previous_time:
            raise LedgerError("ledger timestamps must be strictly increasing")
        previous_time = current_time

        experiment_id = event["experiment_id"]
        experiment = state.setdefault(
            experiment_id,
            {
                "dataset": None,
                "max_rank": -1,
                "operation_status": {},
                "pending": None,
                "closed": False,
            },
        )
        if experiment["closed"]:
            raise LedgerError(f"event after closed experiment {experiment_id}")
        operation = event["operation"]
        status = event["status"]
        rank = OPERATION_RANK[operation]
        if rank < experiment["max_rank"]:
            raise LedgerError(f"operation order regressed for {experiment_id}")
        if experiment["pending"] is not None and experiment["pending"] != operation:
            raise LedgerError(f"unresolved pending operation for {experiment_id}")
        previous_status = experiment["operation_status"].get(operation)
        if previous_status is not None:
            if previous_status != "pending" or status == "pending":
                raise LedgerError(
                    f"invalid repeated operation lifecycle for {experiment_id}"
                )

        if operation == "baseline":
            if experiment["operation_status"].get("dataset_audit") != "completed":
                raise LedgerError("baseline requires a completed dataset audit")
        elif operation == "evaluation":
            if experiment["operation_status"].get("baseline") != "completed":
                raise LedgerError("evaluation requires a completed baseline")
        elif operation == "closeout":
            audit_status = experiment["operation_status"].get("dataset_audit")
            if audit_status not in {"completed", "failed", "skipped"}:
                raise LedgerError("closeout requires a terminal dataset audit")
            if status == "completed" and audit_status != "completed":
                raise LedgerError("completed closeout requires completed dataset audit")

        if status == "completed":
            if experiment["dataset"] is None:
                experiment["dataset"] = event["dataset"]
            elif event["dataset"] != experiment["dataset"]:
                raise LedgerError(f"experiment identity drift for {experiment_id}")

        experiment["operation_status"][operation] = status
        experiment["max_rank"] = max(experiment["max_rank"], rank)
        experiment["pending"] = operation if status == "pending" else None
        if operation == "closeout" and status in {"completed", "failed", "skipped"}:
            experiment["closed"] = True


def _validate_caller_event(event: Any) -> dict[str, Any]:
    if not isinstance(event, dict):
        raise LedgerError("append payload must be an object")
    forbidden = {"event_id", "timestamp_utc"} & set(event)
    if forbidden:
        raise LedgerError(
            f"caller cannot supply helper-generated fields: {sorted(forbidden)}"
        )
    if set(event) != CALLER_KEYS:
        raise LedgerError(
            f"append payload must be closed; missing={sorted(CALLER_KEYS - set(event))}; "
            f"unknown={sorted(set(event) - CALLER_KEYS)}"
        )
    return event


def _validate_ledger_location(path: Path, root: Path) -> tuple[Path, Path]:
    root = root.absolute()
    path = path.absolute()
    if not root.is_dir() or _is_reparse(root):
        raise LedgerError("project root is missing or is a link/reparse point")
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise LedgerError("ledger path must stay inside the project root") from exc
    current = root
    for part in path.relative_to(root).parts[:-1]:
        current = current / part
        try:
            if _is_reparse(current) or not current.is_dir():
                raise LedgerError("ledger parent is a link/reparse point or not a directory")
        except FileNotFoundError as exc:
            raise LedgerError("ledger parent directory is missing") from exc
    if path.exists() and (_is_reparse(path) or not stat.S_ISREG(path.stat().st_mode)):
        raise LedgerError("ledger must be a regular non-link file")
    return path, Path(os.fspath(path) + ".lock")


def _acquire_lock(lock: Path) -> int:
    try:
        fd = os.open(
            lock,
            os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            0o600,
        )
    except FileExistsError as exc:
        raise LedgerError(
            f"ledger lock exists: {lock.name}; confirm no writer is active before manual removal"
        ) from exc
    metadata = json.dumps(
        {
            "pid": os.getpid(),
            "host": socket.gethostname(),
            "created_utc": system_utc(),
        },
        separators=(",", ":"),
    ).encode("utf-8")
    try:
        written = os.write(fd, metadata)
        if written != len(metadata):
            raise OSError("short lock metadata write")
        os.fsync(fd)
    except OSError:
        os.close(fd)
        try:
            lock.unlink()
        except OSError:
            pass
        raise
    return fd


def _release_lock(fd: int, lock: Path) -> None:
    os.close(fd)
    lock.unlink()


def append_event(
    event: dict[str, Any],
    path: Path = LEDGER,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    """Validate all history plus a candidate, then append exactly one record."""

    event = _validate_caller_event(event)
    path, lock = _validate_ledger_location(path, root)
    lock_fd = _acquire_lock(lock)
    append_started = False
    try:
        prior = read_events(path, root=root)
        complete = {
            **event,
            "event_id": str(uuid.uuid4()),
            "timestamp_utc": system_utc(),
        }
        validate_event(complete, root=root)
        validate_sequence([*prior, complete])
        record = (
            json.dumps(
                complete,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("utf-8")
        flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
        ledger_fd = os.open(path, flags, 0o600)
        append_started = True
        try:
            written = os.write(ledger_fd, record)
            if written != len(record):
                raise OSError("short ledger append")
            os.fsync(ledger_fd)
        finally:
            os.close(ledger_fd)
    except Exception:
        if not append_started:
            _release_lock(lock_fd, lock)
        else:
            # A write/fsync failure can leave an uncertain tail. Retain the
            # fail-closed lock for deliberate crash recovery and inspection.
            os.close(lock_fd)
        raise
    _release_lock(lock_fd, lock)
    return complete


# Compatibility alias: v2 append accepts caller evidence without generated fields.
append = append_event


def validate_ledger(path: Path = LEDGER, *, root: Path = ROOT) -> list[dict[str, Any]]:
    path, _ = _validate_ledger_location(path, root)
    return read_events(path, root=root)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, default=LEDGER)
    parser.add_argument("--root", type=Path, default=ROOT)
    subparsers = parser.add_subparsers(dest="command", required=True)
    append_parser = subparsers.add_parser("append")
    source = append_parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--event-json")
    source.add_argument("--event-file", type=Path)
    subparsers.add_parser("validate")
    args = parser.parse_args(argv)
    try:
        if args.command == "append":
            if args.event_file:
                payload_text = args.event_file.read_text(encoding="utf-8")
            else:
                payload_text = args.event_json
            payload = _parse_json(payload_text, "append payload")
            complete = append_event(payload, args.ledger, root=args.root)
            print(json.dumps(complete, ensure_ascii=False, separators=(",", ":")))
        else:
            events = validate_ledger(args.ledger, root=args.root)
            print(f"valid: experiment ledger ({len(events)} events)")
    except (LedgerError, OSError, UnicodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
