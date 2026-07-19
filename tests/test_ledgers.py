import copy
import hashlib
import json
import sys
import tempfile
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import experiment_ledger as ledger

H1 = "1" * 64
H2 = "2" * 64
H3 = "3" * 64


def runtime():
    return {
        "python_version": "3.13.5",
        "platform": "test-platform",
        "executor": "contract-test",
        "packages": {"scikit-learn": "1.7.0"},
    }


def dataset():
    return {
        "name": "conversion-events-v1",
        "source": "internal-governed-snapshot",
        "license": "internal-approved-use",
        "fingerprint_sha256": H1,
        "target": {
            "column": "converted",
            "task_type": "binary_classification",
            "positive_class": 1,
        },
    }


def pipeline():
    return {
        "library": "sklearn",
        "class": "sklearn.pipeline.Pipeline",
        "steps": [
            {
                "name": "preprocess",
                "class": "sklearn.compose.ColumnTransformer",
                "params": {"remainder": "drop"},
            },
            {
                "name": "model",
                "class": "sklearn.linear_model.LogisticRegression",
                "params": {"C": 1.0, "random_state": 17},
            },
        ],
    }


def baseline_cv():
    return {
        "baseline_model": {
            "class": "sklearn.linear_model.LogisticRegression",
            "params": {"C": 1.0, "random_state": 17},
        },
        "cv": {
            "strategy": "StratifiedKFold",
            "folds": 5,
            "shuffle": True,
            "random_state": 17,
        },
        "metrics": {"roc_auc_mean": 0.71, "average_precision_mean": 0.36},
        "primary_metric": "roc_auc_mean",
    }


def caller_event(operation="dataset_audit", status="completed", experiment_id="exp-001"):
    event = {
        "schema_version": "2.0",
        "experiment_id": experiment_id,
        "operation": operation,
        "status": status,
        "commands": [],
        "runtime": None,
        "dataset": None,
        "leakage_audit": None,
        "split": None,
        "features": None,
        "pipeline": None,
        "baseline_cv": None,
        "calibration": None,
        "threshold": None,
        "artifacts": [],
        "decision": {"action": "pending", "rationale": "Awaiting approved action."},
    }
    if status == "completed":
        event["commands"] = [f"python run_{operation}.py --config approved.json"]
        event["runtime"] = runtime()
        event["dataset"] = dataset()
        event["decision"] = {
            "action": "continue" if operation != "closeout" else "freeze",
            "rationale": f"{operation} evidence satisfies its acceptance contract.",
        }
        if operation == "dataset_audit":
            event["leakage_audit"] = {
                "checked": True,
                "methods": ["target-origin review", "post-outcome feature review"],
                "findings": [],
                "prohibited_features": ["converted", "conversion_timestamp"],
            }
            event["split"] = {
                "strategy": "random",
                "random_state": 17,
                "stratified": True,
                "stratify_by": "converted",
                "train_fingerprint_sha256": H2,
                "test_fingerprint_sha256": H3,
            }
            event["features"] = {
                "included": ["channel", "sessions"],
                "categorical": ["channel"],
                "numeric": ["sessions"],
                "excluded": ["converted", "conversion_timestamp"],
            }
        elif operation == "baseline":
            event["pipeline"] = pipeline()
            event["baseline_cv"] = baseline_cv()
        elif operation == "evaluation":
            event["pipeline"] = pipeline()
            event["baseline_cv"] = baseline_cv()
            event["calibration"] = {
                "method": "sigmoid",
                "cv_folds": 5,
                "metrics_before": {"brier": 0.20},
                "metrics_after": {"brier": 0.18},
            }
            event["threshold"] = {
                "value": 0.42,
                "objective": "maximize expected conversion intervention value",
                "selection_split": "train_cv_oof",
                "metric_name": "f1",
                "metric_value": 0.48,
            }
    elif status == "failed":
        event["commands"] = [f"python run_{operation}.py --config approved.json"]
        event["runtime"] = runtime()
        event["decision"] = {
            "action": "change",
            "rationale": "The attempted command failed before producing valid results.",
        }
    elif status == "skipped":
        event["decision"] = {
            "action": "stop",
            "rationale": "The approved stage was intentionally skipped without results.",
        }
    return event


def stored(caller, sequence):
    event = copy.deepcopy(caller)
    event["event_id"] = str(uuid.UUID(int=sequence, version=4))
    event["timestamp_utc"] = f"2026-01-01T00:00:{sequence:02d}.000000Z"
    return event


class ExperimentContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "reports").mkdir()
        self.path = self.root / "reports" / "experiment_ledger.jsonl"

    def tearDown(self):
        self.temp.cleanup()

    def append_chain_to(self, operation, experiment_id="exp-001"):
        if operation in {"baseline", "evaluation", "closeout"}:
            ledger.append_event(
                caller_event("dataset_audit", experiment_id=experiment_id),
                self.path,
                root=self.root,
            )
        if operation == "evaluation":
            ledger.append_event(
                caller_event("baseline", experiment_id=experiment_id),
                self.path,
                root=self.root,
            )

    def test_all_operation_and_status_contract_families(self):
        for operation in ledger.OPERATIONS:
            for status in ledger.STATUSES:
                with self.subTest(operation=operation, status=status):
                    complete = stored(caller_event(operation, status), 1)
                    ledger.validate_event(complete, root=self.root)

    def test_helper_generates_uuid4_and_system_utc_and_cleans_lock(self):
        before = datetime.now(timezone.utc)
        result = ledger.append_event(
            caller_event(), self.path, root=self.root
        )
        after = datetime.now(timezone.utc)
        self.assertEqual(uuid.UUID(result["event_id"]).version, 4)
        timestamp = datetime.fromisoformat(
            result["timestamp_utc"][:-1] + "+00:00"
        )
        self.assertLessEqual(before, timestamp)
        self.assertLessEqual(timestamp, after)
        self.assertFalse(Path(str(self.path) + ".lock").exists())
        self.assertEqual(ledger.validate_ledger(self.path, root=self.root), [result])

    def test_caller_cannot_supply_generated_fields_and_failure_is_byte_identical(self):
        first = ledger.append_event(caller_event(), self.path, root=self.root)
        original = self.path.read_bytes()
        bad = caller_event("closeout")
        bad["event_id"] = first["event_id"]
        bad["timestamp_utc"] = first["timestamp_utc"]
        with self.assertRaises(ledger.LedgerError):
            ledger.append_event(bad, self.path, root=self.root)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertFalse(Path(str(self.path) + ".lock").exists())

    def test_invalid_timestamp_duplicate_id_identity_drift_and_order(self):
        audit = stored(caller_event("dataset_audit"), 1)
        baseline = stored(caller_event("baseline"), 2)
        evaluation = stored(caller_event("evaluation"), 3)
        ledger.validate_sequence([audit, baseline, evaluation])

        invalid_time = copy.deepcopy(audit)
        invalid_time["timestamp_utc"] = "2026-99-99T25:61:61Z"
        with self.assertRaises(ledger.LedgerError):
            ledger.validate_event(invalid_time, root=self.root)

        duplicate = copy.deepcopy(baseline)
        duplicate["event_id"] = audit["event_id"]
        with self.assertRaises(ledger.LedgerError):
            ledger.validate_sequence([audit, duplicate])

        drift = copy.deepcopy(baseline)
        drift["dataset"]["fingerprint_sha256"] = "a" * 64
        with self.assertRaises(ledger.LedgerError):
            ledger.validate_sequence([audit, drift])

        regressed = stored(caller_event("dataset_audit"), 4)
        with self.assertRaises(ledger.LedgerError):
            ledger.validate_sequence([audit, baseline, regressed])

        reversed_time = copy.deepcopy(baseline)
        reversed_time["timestamp_utc"] = audit["timestamp_utc"]
        with self.assertRaises(ledger.LedgerError):
            ledger.validate_sequence([audit, reversed_time])

    def test_validate_ledger_rejects_invalid_timestamp_without_mutation(self):
        event = stored(caller_event(), 1)
        event["timestamp_utc"] = "2026-02-30T00:00:00Z"
        self.path.write_text(json.dumps(event) + "\n", encoding="utf-8")
        original = self.path.read_bytes()
        with self.assertRaises(ledger.LedgerError):
            ledger.validate_ledger(self.path, root=self.root)
        self.assertEqual(self.path.read_bytes(), original)

    def test_lifecycle_prerequisites_pending_resolution_and_closeout_terminal(self):
        with self.assertRaises(ledger.LedgerError):
            ledger.validate_sequence([stored(caller_event("baseline"), 1)])

        pending = stored(caller_event("dataset_audit", "pending"), 1)
        later = stored(caller_event("baseline", "pending"), 2)
        with self.assertRaises(ledger.LedgerError):
            ledger.validate_sequence([pending, later])

        audit = stored(caller_event("dataset_audit"), 1)
        closeout = stored(caller_event("closeout"), 2)
        extra = stored(caller_event("closeout", "failed"), 3)
        with self.assertRaises(ledger.LedgerError):
            ledger.validate_sequence([audit, closeout, extra])

    def test_malformed_empty_runtime_pipeline_and_modeling_evidence(self):
        cases = []
        empty_runtime = stored(caller_event(), 1)
        empty_runtime["runtime"] = {}
        cases.append(empty_runtime)

        empty_pipeline = stored(caller_event("baseline"), 1)
        empty_pipeline["pipeline"] = {}
        cases.append(empty_pipeline)

        empty_steps = stored(caller_event("baseline"), 1)
        empty_steps["pipeline"]["steps"] = []
        cases.append(empty_steps)

        empty_model_params = stored(caller_event("baseline"), 1)
        empty_model_params["baseline_cv"]["baseline_model"]["params"] = {}
        cases.append(empty_model_params)

        empty_metrics = stored(caller_event("baseline"), 1)
        empty_metrics["baseline_cv"]["metrics"] = {}
        cases.append(empty_metrics)

        bad_folds = stored(caller_event("baseline"), 1)
        bad_folds["baseline_cv"]["cv"]["folds"] = 1
        cases.append(bad_folds)

        empty_step_params = stored(caller_event("baseline"), 1)
        empty_step_params["pipeline"]["steps"][0]["params"] = {}
        cases.append(empty_step_params)

        empty_calibration = stored(caller_event("evaluation"), 1)
        empty_calibration["calibration"] = {}
        cases.append(empty_calibration)

        bad_threshold = stored(caller_event("evaluation"), 1)
        bad_threshold["threshold"]["value"] = 1.5
        cases.append(bad_threshold)

        for case in cases:
            with self.subTest(case=cases.index(case)):
                with self.assertRaises(ledger.LedgerError):
                    ledger.validate_event(case, root=self.root)

    def test_dataset_leakage_split_and_pipeline_semantics(self):
        cases = []
        license_placeholder = stored(caller_event(), 1)
        license_placeholder["dataset"]["license"] = "unknown"
        cases.append(license_placeholder)

        bad_fingerprint = stored(caller_event(), 1)
        bad_fingerprint["dataset"]["fingerprint_sha256"] = "xyz"
        cases.append(bad_fingerprint)

        source_placeholder = stored(caller_event(), 1)
        source_placeholder["dataset"]["source"] = "placeholder"
        cases.append(source_placeholder)

        bad_target = stored(caller_event(), 1)
        bad_target["dataset"]["target"]["task_type"] = "regression"
        cases.append(bad_target)

        leaked_target = stored(caller_event(), 1)
        leaked_target["features"]["included"].append("converted")
        leaked_target["features"]["numeric"].append("converted")
        cases.append(leaked_target)

        wrong_stratification = stored(caller_event(), 1)
        wrong_stratification["split"]["stratify_by"] = "channel"
        cases.append(wrong_stratification)

        missing_random_state = stored(caller_event(), 1)
        missing_random_state["split"]["random_state"] = None
        cases.append(missing_random_state)

        duplicate_split_fingerprint = stored(caller_event(), 1)
        duplicate_split_fingerprint["split"]["test_fingerprint_sha256"] = H2
        cases.append(duplicate_split_fingerprint)

        bad_pipeline_class = stored(caller_event("baseline"), 1)
        bad_pipeline_class["pipeline"]["class"] = "CustomPipeline"
        cases.append(bad_pipeline_class)

        model_mismatch = stored(caller_event("baseline"), 1)
        model_mismatch["baseline_cv"]["baseline_model"][
            "class"
        ] = "sklearn.ensemble.RandomForestClassifier"
        cases.append(model_mismatch)

        for case in cases:
            with self.subTest(case=cases.index(case)):
                with self.assertRaises(ledger.LedgerError):
                    ledger.validate_event(case, root=self.root)

    def artifact_event(self, path, digest):
        event = stored(caller_event(), 1)
        event["artifacts"] = [{"path": path, "sha256": digest}]
        return event

    def test_artifact_regular_file_hash_and_all_path_failures(self):
        artifact = self.root / "reports" / "audit.txt"
        artifact.write_bytes(b"audited")
        digest = hashlib.sha256(b"audited").hexdigest()
        ledger.validate_event(
            self.artifact_event("reports/audit.txt", digest), root=self.root
        )

        cases = [
            self.artifact_event("../outside.txt", digest),
            self.artifact_event("reports/missing.txt", digest),
            self.artifact_event("reports/audit.txt", "z" * 64),
            self.artifact_event("reports/audit.txt", "0" * 64),
            self.artifact_event("reports\\audit.txt", digest),
        ]
        for case in cases:
            with self.subTest(case=cases.index(case)):
                with self.assertRaises(ledger.LedgerError):
                    ledger.validate_event(case, root=self.root)

    def _symlink_or_skip(self, link: Path, target: Path, directory=False):
        try:
            link.symlink_to(target, target_is_directory=directory)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlinks unavailable: {exc}")

    def test_artifact_symlink_file_and_parent_rejected(self):
        real = self.root / "reports" / "real.txt"
        real.write_bytes(b"real")
        digest = hashlib.sha256(b"real").hexdigest()
        link = self.root / "reports" / "link.txt"
        self._symlink_or_skip(link, real)
        with self.assertRaises(ledger.LedgerError):
            ledger.validate_event(
                self.artifact_event("reports/link.txt", digest), root=self.root
            )
        link.unlink()

        real_dir = self.root / "artifact-real"
        real_dir.mkdir()
        (real_dir / "value.txt").write_bytes(b"real")
        linked_dir = self.root / "artifact-link"
        self._symlink_or_skip(linked_dir, real_dir, directory=True)
        with self.assertRaises(ledger.LedgerError):
            ledger.validate_event(
                self.artifact_event("artifact-link/value.txt", digest),
                root=self.root,
            )

    def test_concurrent_or_stale_lock_fails_closed_without_mutation(self):
        self.path.write_bytes(b"")
        lock = Path(str(self.path) + ".lock")
        lock.write_text('{"pid":999999,"created_utc":"stale"}', encoding="utf-8")
        original = self.path.read_bytes()
        with self.assertRaises(ledger.LedgerError):
            ledger.append_event(caller_event(), self.path, root=self.root)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertTrue(lock.exists())

    def test_validation_error_cleans_lock_and_preserves_existing_bytes(self):
        ledger.append_event(caller_event(), self.path, root=self.root)
        original = self.path.read_bytes()
        bad = caller_event("closeout")
        bad["decision"]["rationale"] = ""
        with self.assertRaises(ledger.LedgerError):
            ledger.append_event(bad, self.path, root=self.root)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertFalse(Path(str(self.path) + ".lock").exists())

    def test_entire_existing_jsonl_is_validated_before_candidate(self):
        self.path.write_text('{"malformed":true}\n', encoding="utf-8")
        original = self.path.read_bytes()
        with self.assertRaises(ledger.LedgerError):
            ledger.append_event(caller_event(), self.path, root=self.root)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertFalse(Path(str(self.path) + ".lock").exists())

    def test_noncompleted_statuses_cannot_fabricate_results(self):
        for status in ("failed", "skipped", "pending"):
            with self.subTest(status=status):
                event = stored(caller_event("dataset_audit", status), 1)
                event["dataset"] = dataset()
                with self.assertRaises(ledger.LedgerError):
                    ledger.validate_event(event, root=self.root)


if __name__ == "__main__":
    unittest.main()
