from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO

from vassago_contract_runtime.cli import main


def _main(args: list[str]) -> int:
    with redirect_stdout(StringIO()):
        return main(args)


def _main_stdout(args: list[str]) -> tuple[int, str]:
    output = StringIO()
    with redirect_stdout(output):
        code = main(args)
    return code, output.getvalue()


class CliTests(unittest.TestCase):
    def test_check_passes(self) -> None:
        self.assertEqual(_main(["check"]), 0)

    def test_run_design_dry_run_writes_manifest_and_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            code = _main(
                [
                    "run-design",
                    "--design",
                    "sc01-access",
                    "--targets",
                    "tests/fixtures/targets.json",
                    "--output",
                    str(run_dir),
                    "--dry-run",
                ]
            )

            self.assertEqual(code, 0)
            manifest = json.loads((run_dir / "run-manifest.json").read_text(encoding="utf-8"))
            target_id = manifest["targets"][0]["target_id"]
            self.assertEqual(manifest["summary"]["status"], "completed")
            self.assertTrue((run_dir / "targets" / target_id / "phases" / "00_intake" / "target-manifest.json").is_file())

    def test_resume_dry_run_skips_completed_phases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            first = _main(
                [
                    "run-design",
                    "--design",
                    "sc01-access",
                    "--targets",
                    "tests/fixtures/targets.json",
                    "--output",
                    str(run_dir),
                    "--dry-run",
                ]
            )
            second = _main(["resume", "--run", str(run_dir), "--dry-run"])

            self.assertEqual(first, 0)
            self.assertEqual(second, 0)
            manifest = json.loads((run_dir / "run-manifest.json").read_text(encoding="utf-8"))
            self.assertGreaterEqual(manifest["summary"]["skipped_count"], 11)

    def test_artifact_read_returns_json_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            self.assertEqual(
                _main(
                    [
                        "run-design",
                        "--design",
                        "sc01-access",
                        "--targets",
                        "tests/fixtures/targets.json",
                        "--output",
                        str(run_dir),
                        "--dry-run",
                    ]
                ),
                0,
            )
            manifest = json.loads((run_dir / "run-manifest.json").read_text(encoding="utf-8"))
            target_id = manifest["targets"][0]["target_id"]
            uri = f"vassago://runs/{manifest['run_id']}/targets/{target_id}/phases/00_intake/target-manifest.json"

            code, stdout = _main_stdout(["artifact-read", "--run", str(run_dir), "--uri", uri])

            self.assertEqual(code, 0)
            payload = json.loads(stdout)
            self.assertEqual(payload["phase_id"], "00_intake")


if __name__ == "__main__":
    unittest.main()
