import shutil
import subprocess
import sys
import tempfile
import unittest
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SelfContainedAdapterTests(unittest.TestCase):
    def test_isolated_copy_runs_all_local_validators(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory) / "adapter"
            shutil.copytree(
                ROOT,
                fixture,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
            commands = [
                [sys.executable, "tools/validate_core_pin.py"],
                [sys.executable, "tools/experiment_ledger.py", "validate"],
                [sys.executable, "tools/agent_ledger.py", "validate"],
                [sys.executable, "tools/validate_orchestration.py"],
            ]
            for command in commands:
                with self.subTest(command=command):
                    result = subprocess.run(
                        command,
                        cwd=fixture,
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                    self.assertEqual(
                        result.returncode,
                        0,
                        msg=f"stdout={result.stdout}\nstderr={result.stderr}",
                    )
            entrypoint = fixture / "docs" / "agent_orchestration.md"
            for relative in re.findall(
                r"\[[^\]]+\]\(([^)]+)\)",
                entrypoint.read_text(encoding="utf-8"),
            ):
                with self.subTest(document_link=relative):
                    self.assertTrue((entrypoint.parent / relative).is_file())


if __name__ == "__main__":
    unittest.main()
