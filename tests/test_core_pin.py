import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import validate_core_pin as pin


class CorePinContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.fixture = Path(self.temp.name) / "target"
        self.fixture.mkdir()
        self.lock = json.loads(
            (ROOT / "orchestration.lock.json").read_text(encoding="utf-8")
        )
        for target_path in pin.CRITICAL_MANAGED_FILES:
            source = ROOT / target_path
            destination = self.fixture / target_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        self.write_lock()

    def tearDown(self):
        self.temp.cleanup()

    def write_lock(self):
        (self.fixture / "orchestration.lock.json").write_text(
            json.dumps(self.lock), encoding="utf-8"
        )

    def assert_invalid(self):
        self.write_lock()
        with self.assertRaises(pin.PinError):
            pin.validate_pin(root=self.fixture)

    def test_local_pin_is_self_contained_and_complete(self):
        result = pin.validate_pin(root=self.fixture)
        self.assertEqual(
            {entry["target_path"] for entry in result["managed_files"]},
            set(pin.CRITICAL_MANAGED_FILES),
        )
        self.assertTrue(
            {
                "PROJECT_LOG.md",
                "reports/agent_execution_ledger.jsonl",
                "reports/experiment_ledger.jsonl",
            }.isdisjoint(pin.CRITICAL_MANAGED_FILES)
        )

    def test_rejects_closed_shape_and_incomplete_extra_duplicate_unknown_mapping(self):
        cases = []
        incomplete = copy.deepcopy(self.lock)
        incomplete["managed_files"].pop()
        cases.append(incomplete)

        extra = copy.deepcopy(self.lock)
        extra["unexpected"] = True
        cases.append(extra)

        extra_mapping = copy.deepcopy(self.lock)
        extra_mapping["managed_files"].append(
            copy.deepcopy(extra_mapping["managed_files"][0])
        )
        cases.append(extra_mapping)

        duplicate = copy.deepcopy(self.lock)
        duplicate["managed_files"][-1] = copy.deepcopy(
            duplicate["managed_files"][0]
        )
        cases.append(duplicate)

        unknown = copy.deepcopy(self.lock)
        unknown_entry = unknown["managed_files"][-1]
        unknown_entry["target_path"] = "unknown.txt"
        unknown_entry["core_path"] = "unknown.txt"
        (self.fixture / "unknown.txt").write_text("unknown", encoding="utf-8")
        digest = hashlib.sha256(b"unknown").hexdigest()
        unknown_entry["target_sha256"] = digest
        unknown_entry["core_sha256"] = digest
        cases.append(unknown)

        for bad_lock in cases:
            with self.subTest(case=cases.index(bad_lock)):
                self.lock = bad_lock
                self.assert_invalid()

    def test_rejects_parent_escape_and_noncanonical_paths(self):
        for bad_path in (
            "../outside.txt",
            "docs/../VERSION",
            "/absolute.txt",
            "C:/outside.txt",
            "docs\\architecture.md",
        ):
            with self.subTest(path=bad_path):
                bad = copy.deepcopy(self.lock)
                bad["managed_files"][0]["target_path"] = bad_path
                self.lock = bad
                self.assert_invalid()

    def test_rejects_target_tamper_nonhex_and_relationship_mismatch(self):
        (self.fixture / "VERSION").write_text("tampered\n", encoding="utf-8")
        with self.assertRaises(pin.PinError):
            pin.validate_pin(root=self.fixture)

        shutil.copy2(ROOT / "VERSION", self.fixture / "VERSION")
        bad_hash = copy.deepcopy(self.lock)
        bad_hash["managed_files"][-1]["target_sha256"] = "g" * 64
        self.lock = bad_hash
        self.assert_invalid()

        relationship = copy.deepcopy(
            json.loads((ROOT / "orchestration.lock.json").read_text())
        )
        relationship["managed_files"][0]["relationship"] = "exact_copy"
        self.lock = relationship
        self.assert_invalid()

    def _symlink_or_skip(self, link: Path, target: Path, directory=False):
        try:
            link.symlink_to(target, target_is_directory=directory)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlinks unavailable: {exc}")

    def test_rejects_symlink_managed_file(self):
        target = self.fixture / "VERSION"
        real = self.fixture / "VERSION.real"
        target.replace(real)
        self._symlink_or_skip(target, real)
        with self.assertRaises(pin.PinError):
            pin.validate_pin(root=self.fixture)

    def test_rejects_symlink_parent(self):
        link = self.fixture / ".codex"
        real = self.fixture / ".codex.real"
        link.replace(real)
        self._symlink_or_skip(link, real, directory=True)
        with self.assertRaises(pin.PinError):
            pin.validate_pin(root=self.fixture)

    def create_core_checkout(self):
        core = Path(self.temp.name) / "core"
        core.mkdir()
        entries = {
            entry["target_path"]: entry for entry in self.lock["managed_files"]
        }
        for target_path, (core_path, relationship) in pin.CRITICAL_MANAGED_FILES.items():
            destination = core / core_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            if relationship == "exact_copy":
                shutil.copy2(self.fixture / target_path, destination)
            else:
                destination.write_text(
                    f"fixture Core source for {core_path}\n", encoding="utf-8"
                )
                entries[target_path]["core_sha256"] = hashlib.sha256(
                    destination.read_bytes()
                ).hexdigest()
        subprocess.run(["git", "init", "-q", core], check=True)
        subprocess.run(
            ["git", "-C", core, "config", "user.email", "test@example.invalid"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", core, "config", "user.name", "Contract Test"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", core, "config", "core.autocrlf", "false"],
            check=True,
        )
        subprocess.run(["git", "-C", core, "add", "."], check=True)
        subprocess.run(
            ["git", "-C", core, "commit", "-q", "-m", "fixture"], check=True
        )
        commit = subprocess.check_output(
            ["git", "-C", core, "rev-parse", "HEAD"], text=True
        ).strip()
        self.lock["core_commit"] = commit
        self.write_lock()
        return core

    def test_explicit_core_validates_commit_version_and_source_hashes(self):
        core = self.create_core_checkout()
        pin.validate_pin(root=self.fixture, core_root=core)

        self.lock["core_commit"] = "0" * 40
        self.write_lock()
        with self.assertRaises(pin.PinError):
            pin.validate_pin(root=self.fixture, core_root=core)

        self.lock["core_commit"] = subprocess.check_output(
            ["git", "-C", core, "rev-parse", "HEAD"], text=True
        ).strip()
        self.write_lock()
        (core / "AGENTS.md").write_text("tampered", encoding="utf-8")
        with self.assertRaises(pin.PinError):
            pin.validate_pin(root=self.fixture, core_root=core)


if __name__ == "__main__":
    unittest.main()
