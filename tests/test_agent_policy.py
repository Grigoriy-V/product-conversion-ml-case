from __future__ import annotations

import json
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AgentPolicyTests(unittest.TestCase):
    def test_root_policy_is_complete_and_standalone(self) -> None:
        policy = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        required = (
            "supervisor-only",
            "one primary worker",
            "luna_clerk",
            "terra_worker",
            "sol_specialist",
            "human-gated",
            "tools/agent_ledger.py",
            "tools/experiment_ledger.py",
            "system UTC",
            "sklearn.pipeline.Pipeline",
            "leakage",
            "split strategy",
            "event ID",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, policy)
        self.assertNotIn("does not replace them", policy)

    def test_profiles_have_exact_routing_and_substantial_instructions(self) -> None:
        expected = {
            "luna_clerk.toml": ("gpt-5.6-luna", "none"),
            "terra_worker.toml": ("gpt-5.6-terra", "low"),
            "sol_specialist.toml": ("gpt-5.6-sol", "high"),
        }
        for filename, (model, effort) in expected.items():
            with self.subTest(profile=filename):
                profile = tomllib.loads(
                    (ROOT / ".codex" / "agents" / filename).read_text(
                        encoding="utf-8"
                    )
                )
                self.assertEqual(model, profile["model"])
                self.assertEqual(effort, profile["model_reasoning_effort"])
                instructions = profile["developer_instructions"]
                self.assertGreater(len(instructions), 500)
                self.assertIn("may not change your model or reasoning level", instructions)
                self.assertIn("may not", instructions)
                self.assertIn("tools/agent_ledger.py", instructions)

    def test_luna_is_clerical_only(self) -> None:
        profile = tomllib.loads(
            (ROOT / ".codex" / "agents" / "luna_clerk.toml").read_text(
                encoding="utf-8"
            )
        )
        instructions = profile["developer_instructions"]
        self.assertIn("Do not inspect or modify implementation code", instructions)
        self.assertIn("must not make project or ML decisions", (
            ROOT / "AGENTS.md"
        ).read_text(encoding="utf-8"))

    def test_local_docs_disclaim_runtime_inheritance(self) -> None:
        orchestration = (ROOT / "docs" / "agent_orchestration.md").read_text(
            encoding="utf-8"
        )
        contract = (ROOT / "docs" / "project_adapter_contract.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("standalone operating procedure", orchestration)
        self.assertIn("operationally self-contained", contract)
        self.assertIn("neither required nor assumed", contract)
        self.assertIn("Provenance is not live policy inheritance", contract)

    def test_adapted_policy_files_are_pinned_as_adapted(self) -> None:
        lock = json.loads(
            (ROOT / "orchestration.lock.json").read_text(encoding="utf-8")
        )
        relationships = {
            entry["target_path"]: entry["relationship"]
            for entry in lock["managed_files"]
        }
        for target in (
            "AGENTS.md",
            ".codex/agents/luna_clerk.toml",
            ".codex/agents/terra_worker.toml",
            ".codex/agents/sol_specialist.toml",
            "docs/agent_orchestration.md",
        ):
            with self.subTest(target=target):
                self.assertEqual("adapted", relationships[target])


if __name__ == "__main__":
    unittest.main()
