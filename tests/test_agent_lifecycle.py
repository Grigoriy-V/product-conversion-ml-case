import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import agent_ledger


class IsolatedAgentLifecycleTests(unittest.TestCase):
    def invoke(self, arguments):
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            return agent_ledger.main(arguments)

    def test_start_terminal_supervisor_review_lifecycle(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "agent.jsonl"
            metadata = {
                "agent_run_id": "isolated-lifecycle",
                "parent_task": "/root",
                "agent_name": "terra_worker",
                "requested_model": "gpt-5.6-terra",
                "requested_reasoning": "low",
                "task_type": "validation",
                "roadmap_step": None,
                "scope_summary": "Validate a disposable full lifecycle.",
                "constraints": ["No target mutation"],
                "commands": ["isolated start"],
                "files_changed": [],
                "git_commit_before": None,
                "git_commit_after": None,
                "ml_ledger_event_ids": [],
                "notes": "Disposable isolated ledger.",
            }
            common = ["--ledger", str(path)]
            self.assertEqual(
                self.invoke(
                    [
                        *common,
                        "start",
                        "--metadata-json",
                        json.dumps(metadata),
                    ]
                ),
                0,
            )
            self.assertEqual(
                self.invoke(
                    [
                        *common,
                        "terminal",
                        "--run-id",
                        "isolated-lifecycle",
                        "--status",
                        "completed",
                        "--outcome-summary",
                        "Disposable validation passed.",
                        "--files-changed-json",
                        "[]",
                        "--commands-json",
                        '["isolated validation"]',
                    ]
                ),
                0,
            )
            self.assertEqual(
                self.invoke(
                    [
                        *common,
                        "review",
                        "--run-id",
                        "isolated-lifecycle",
                        "--decision",
                        "accept",
                        "--outcome-summary",
                        "Disposable lifecycle accepted.",
                        "--reviewer-agent-name",
                        "root_supervisor",
                        "--reviewer-model",
                        "root-session-model",
                        "--reviewer-reasoning",
                        "not_applicable",
                        "--parent-task",
                        "/root",
                    ]
                ),
                0,
            )
            self.assertEqual(self.invoke([*common, "validate"]), 0)
            events = agent_ledger.read_events(path)
            self.assertEqual(
                [event["event_type"] for event in events],
                ["started", "completed", "reviewed"],
            )
            self.assertIsNone(events[1]["supervisor_decision"])
            self.assertEqual(events[2]["supervisor_decision"], "accept")


if __name__ == "__main__":
    unittest.main()
