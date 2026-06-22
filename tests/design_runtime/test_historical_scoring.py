from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO

from vassago_contract_runtime.cli import main
from vassago_contract_runtime.design_runtime.manifest import atomic_write_json
from vassago_contract_runtime.design_runtime.models import ContractTarget
from vassago_contract_runtime.historical_scoring import build_historical_score, write_historical_score


class HistoricalScoringTests(unittest.TestCase):
    def test_scores_missing_and_runtime_ready_cases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "historical.json"
            run = root / "run"
            case_missing = _case("HEC-X01", "sc01_access_control", "0x1111111111111111111111111111111111111111")
            case_ready = _case("HEC-X02", "proxy_upgrade_signature", "0x2222222222222222222222222222222222222222")
            atomic_write_json(manifest, {"kind": "vassago-historical-exploit-corpus", "version": "test", "cases": [case_missing, case_ready]})
            _write_run_manifest(run)
            _write_final_report(
                run,
                _target(case_ready),
                {
                    "final_status": "runtime_ready_pending_local_execution",
                    "evidence_status": "static_only",
                    "queue_count": 2,
                    "source_truth_verified_count": 1,
                    "compile_status": "compile_only_passed",
                    "runtime_ready_count": 1,
                    "foundry_allowed": True,
                    "runtime_status": None,
                },
            )

            score = build_historical_score(run, manifest)

            self.assertEqual(score["status"], "completed")
            self.assertEqual(score["summary"]["case_count"], 2)
            self.assertEqual(score["summary"]["missing_final_report_count"], 1)
            self.assertEqual(score["summary"]["runtime_ready_count"], 1)
            self.assertEqual(score["summary"]["actionable_count"], 1)
            self.assertEqual(score["summary"]["by_family_signal"]["sc01_access_control"]["missing"], 1)
            self.assertEqual(score["summary"]["by_family_signal"]["proxy_upgrade_signature"]["runtime_ready"], 1)

    def test_write_score_and_cli_emit_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "historical.json"
            run = root / "run"
            output = root / "score"
            case = _case("HEC-X03", "bridge_message_auth", "0x3333333333333333333333333333333333333333")
            atomic_write_json(manifest, {"kind": "vassago-historical-exploit-corpus", "version": "test", "cases": [case]})
            _write_run_manifest(run)
            _write_final_report(
                run,
                _target(case),
                {
                    "final_status": "blocked_no_runtime_ready",
                    "evidence_status": "static_only",
                    "queue_count": 1,
                    "source_truth_verified_count": 0,
                    "compile_status": None,
                    "runtime_ready_count": 0,
                    "foundry_allowed": False,
                    "runtime_status": None,
                },
            )

            result = write_historical_score(run, manifest, output_dir=output)

            self.assertEqual(result["status"], "completed")
            self.assertTrue((output / "historical-corpus-score.json").is_file())
            self.assertTrue((output / "historical-corpus-score.md").is_file())
            payload = json.loads((output / "historical-corpus-score.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["candidate_count"], 1)
            filtered = build_historical_score(run, manifest, benchmark_id="HEC-X03")
            self.assertEqual(filtered["summary"]["case_count"], 1)
            self.assertEqual(filtered["summary"]["candidate_count"], 1)

            with redirect_stdout(StringIO()):
                code = main(
                    [
                        "historical-corpus-score",
                        "--run",
                        str(run),
                        "--manifest",
                        str(manifest),
                        "--benchmark-id",
                        "HEC-X03",
                        "--output-dir",
                        str(output / "cli"),
                    ]
                )

            self.assertEqual(code, 0)
            self.assertTrue((output / "cli" / "historical-corpus-score.json").is_file())


def _case(benchmark_id: str, family: str, address: str) -> dict[str, object]:
    return {
        "benchmark_id": benchmark_id,
        "case_id": benchmark_id.lower(),
        "family": family,
        "blind_inputs": {
            "chain": "ethereum",
            "target_address": address,
            "source_repo_path": f"src/test/{benchmark_id}.sol",
            "has_foundry_poc": True,
        },
        "hidden_ground_truth": {
            "attack_txs": ["0x" + "aa" * 32],
            "fork_blocks": ["123"],
            "vulnerable_contracts": [address],
            "loss_label": "test",
        },
    }


def _target(case: dict[str, object]) -> ContractTarget:
    blind = case["blind_inputs"]
    assert isinstance(blind, dict)
    return ContractTarget(chain=str(blind["chain"]), address=str(blind["target_address"]))


def _write_run_manifest(run: Path) -> None:
    run.mkdir(parents=True, exist_ok=True)
    atomic_write_json(run / "run-manifest.json", {"run_id": "RUN-test", "summary": {"status": "completed"}})


def _write_final_report(run: Path, target: ContractTarget, payload: dict[str, object]) -> None:
    path = run / "targets" / target.target_id / "phases" / "10_final_report" / "sc01-final-report.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(path, {"status": "completed", "target_id": target.target_id, **payload})


if __name__ == "__main__":
    unittest.main()
