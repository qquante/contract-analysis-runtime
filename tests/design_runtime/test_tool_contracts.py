from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from vassago_contract_runtime.tools import ToolInvocation, build_runtime_tool_registry


TARGET = {"chain": "eth", "address": "0x1111111111111111111111111111111111111111"}


class ToolContractTests(unittest.TestCase):
    def test_runtime_registry_exposes_campaign_level_tools(self) -> None:
        registry = build_runtime_tool_registry()

        names = {item["name"] for item in registry.list_contracts()}

        self.assertEqual(
            names,
            {"vassago_design_run", "vassago_design_resume", "vassago_artifact_read"},
        )
        design_run = registry.describe("run_design")
        self.assertEqual(design_run["name"], "vassago_design_run")
        self.assertEqual(design_run["policy"]["no_broadcast"], True)
        self.assertIn("filesystem_write_artifacts", design_run["effects"])

    def test_design_run_and_artifact_read_tools_use_real_runtime(self) -> None:
        registry = build_runtime_tool_registry()
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            run_result = registry.invoke(
                ToolInvocation(
                    "vassago_design_run",
                    {
                        "design": "sc01-access",
                        "targets": [TARGET],
                        "output": str(run_dir),
                        "bootstrap_adapters": True,
                        "source_fixture": "tests/fixtures/source_fixture.json",
                    },
                    agent_id="test-agent",
                )
            )

            self.assertEqual(run_result.status, "completed")
            output = run_result.output
            self.assertEqual(output["failed_count"], 0)
            target_id = "CT-3c443b782288"
            uri = f"vassago://runs/{output['run_id']}/targets/{target_id}/phases/10_final_report/sc01-final-report.json"
            read_result = registry.invoke(
                ToolInvocation("vassago_artifact_read", {"run": str(run_dir), "uri": uri}, agent_id="test-agent")
            )

            self.assertEqual(read_result.status, "completed")
            self.assertEqual(read_result.output["artifact_type"], "json")
            self.assertEqual(read_result.output["artifact"]["final_status"], "blocked_no_runtime_ready")

    def test_design_resume_tool_resumes_existing_run(self) -> None:
        registry = build_runtime_tool_registry()
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            first = registry.invoke(
                ToolInvocation(
                    "vassago_design_run",
                    {
                        "design": "sc01-access",
                        "targets": [TARGET],
                        "output": str(run_dir),
                        "dry_run": True,
                    },
                )
            )
            second = registry.invoke(
                ToolInvocation("vassago_design_resume", {"run": str(run_dir), "dry_run": True})
            )

            self.assertEqual(first.status, "completed")
            self.assertEqual(second.status, "completed")
            self.assertGreaterEqual(second.output["skipped_count"], 11)

    def test_unknown_tool_fails_closed(self) -> None:
        registry = build_runtime_tool_registry()

        result = registry.invoke(ToolInvocation("vassago_shell", {}))

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.error["code"], "ValueError")


if __name__ == "__main__":
    unittest.main()
