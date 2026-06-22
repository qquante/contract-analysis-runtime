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
from vassago_contract_runtime.historical_stage_report import build_historical_stage_report, write_historical_stage_report


class HistoricalStageReportTests(unittest.TestCase):
    def test_reports_source_truth_and_no_candidate_stages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "historical.json"
            run = root / "run"
            source_blocked = _case("HEC-X01", "proxy_upgrade_signature", "0x1111111111111111111111111111111111111111")
            no_candidate = _case("HEC-X02", "oracle_accounting", "0x2222222222222222222222222222222222222222")
            atomic_write_json(
                manifest,
                {"kind": "vassago-historical-exploit-corpus", "version": "test", "cases": [source_blocked, no_candidate]},
            )
            _write_run_manifest(run)
            _write_target_artifacts(
                run,
                _target(source_blocked),
                final_report={
                    "final_status": "blocked_no_runtime_ready",
                    "evidence_status": "static_only",
                    "queue_count": 1,
                    "source_truth_verified_count": 0,
                    "compile_status": "compile_skipped_not_ready",
                    "runtime_ready_count": 0,
                    "foundry_allowed": False,
                    "runtime_status": "blocked_no_runtime_ready",
                },
                thesis_queue={
                    "queue_count": 1,
                    "queue": [
                        {
                            "candidate_id": "TC-1",
                            "thesis_id": "uups_weak_auth",
                            "matched_functions": ["upgradeTo(address)"],
                        }
                    ],
                },
                source_truth={
                    "status": "blocked",
                    "blockers": ["manual_or_slither_source_truth_required"],
                    "reviews": [
                        {
                            "candidate_id": "TC-1",
                            "thesis_id": "uups_weak_auth",
                            "matched_functions": ["upgradeTo(address)"],
                            "missing_proof_pieces": ["source_truth_guard_gap"],
                        }
                    ],
                },
                proof_pieces={
                    "blockers": ["source_truth_guard_gap", "actor_model"],
                    "pieces": [
                        {
                            "candidate_id": "TC-1",
                            "thesis_id": "uups_weak_auth",
                            "missing_pieces": ["source_truth_guard_gap", "actor_model"],
                            "state_blockers": ["eip1967_or_explorer_proxy_state_required"],
                        }
                    ],
                },
            )
            _write_target_artifacts(
                run,
                _target(no_candidate),
                final_report={
                    "final_status": "blocked_no_runtime_ready",
                    "evidence_status": "static_only",
                    "queue_count": 0,
                    "source_truth_verified_count": 0,
                    "compile_status": "compile_skipped_not_ready",
                    "runtime_ready_count": 0,
                    "foundry_allowed": False,
                    "runtime_status": "blocked_no_runtime_ready",
                },
                corpus_candidates={"candidate_count": 0, "candidates": []},
            )

            report = build_historical_stage_report(run, manifest)

            self.assertEqual(report["summary"]["case_count"], 2)
            self.assertEqual(report["summary"]["candidate_count"], 1)
            self.assertEqual(report["summary"]["by_stage"]["05_source_truth_not_verified"], 1)
            self.assertEqual(report["summary"]["by_stage"]["04_no_thesis_candidate"], 1)
            first = report["candidate_records"][0]
            self.assertEqual(first["recommended_mapper"], "proxy_upgrade_signature_mapper")
            self.assertIn("source_truth_guard_gap", first["missing_pieces"])
            self.assertIn("uups_weak_auth", first["thesis_ids"])

    def test_write_report_and_cli_emit_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "historical.json"
            run = root / "run"
            output = root / "stage"
            case = _case("HEC-X03", "bridge_message_auth", "0x3333333333333333333333333333333333333333")
            atomic_write_json(manifest, {"kind": "vassago-historical-exploit-corpus", "version": "test", "cases": [case]})
            _write_run_manifest(run)
            _write_target_artifacts(
                run,
                _target(case),
                final_report={
                    "final_status": "runtime_ready_pending_local_execution",
                    "evidence_status": "static_only",
                    "queue_count": 1,
                    "source_truth_verified_count": 1,
                    "compile_status": "compile_only_passed",
                    "runtime_ready_count": 1,
                    "foundry_allowed": True,
                    "runtime_status": None,
                },
            )

            result = write_historical_stage_report(run, manifest, output_dir=output)

            self.assertEqual(result["status"], "completed")
            self.assertTrue((output / "historical-stage-failure-report.json").is_file())
            self.assertTrue((output / "historical-stage-failure-report.md").is_file())
            payload = json.loads((output / "historical-stage-failure-report.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["runtime_ready_count"], 1)

            with redirect_stdout(StringIO()):
                code = main(
                    [
                        "historical-stage-report",
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
            self.assertTrue((output / "cli" / "historical-stage-failure-report.json").is_file())

    def test_runtime_failed_uses_runtime_failed_stage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "historical.json"
            run = root / "run"
            case = _case("HEC-X04", "proxy_upgrade_signature", "0x4444444444444444444444444444444444444444")
            atomic_write_json(manifest, {"kind": "vassago-historical-exploit-corpus", "version": "test", "cases": [case]})
            _write_run_manifest(run)
            _write_target_artifacts(
                run,
                _target(case),
                final_report={
                    "final_status": "runtime_failed",
                    "evidence_status": "inconclusive",
                    "queue_count": 1,
                    "source_truth_verified_count": 1,
                    "compile_status": "compile_only_passed",
                    "runtime_ready_count": 1,
                    "foundry_allowed": True,
                    "runtime_status": "runtime_failed",
                },
            )
            _write(
                run
                / "targets"
                / _target(case).target_id
                / "phases"
                / "09_runtime_foundry"
                / "foundry-runtime-result.json",
                {"status": "runtime_failed", "blockers": ["forge_failed"]},
            )

            report = build_historical_stage_report(run, manifest)

            self.assertEqual(report["summary"]["runtime_ready_count"], 0)
            self.assertEqual(report["summary"]["by_stage"]["09_runtime_failed"], 1)
            self.assertEqual(report["records"][0]["blocking_stage"], "09_runtime_failed")


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


def _write_target_artifacts(
    run: Path,
    target: ContractTarget,
    *,
    final_report: dict[str, object],
    corpus_candidates: dict[str, object] | None = None,
    thesis_queue: dict[str, object] | None = None,
    source_truth: dict[str, object] | None = None,
    proof_pieces: dict[str, object] | None = None,
) -> None:
    target_root = run / "targets" / target.target_id / "phases"
    _write(target_root / "10_final_report" / "sc01-final-report.json", {"status": "completed", "target_id": target.target_id, **final_report})
    _write(target_root / "03_corpus_motifs" / "sc01-thesis-candidates.json", corpus_candidates or {"candidate_count": 1, "candidates": []})
    _write(target_root / "04_thesis_acquisition" / "sc01-thesis-queue.json", thesis_queue or {"queue_count": 0, "queue": []})
    _write(target_root / "05_source_truth" / "sc01-source-truth.json", source_truth or {"status": "blocked", "blockers": []})
    _write(target_root / "07_proof_pieces" / "sc01-proof-piece-state.json", proof_pieces or {"blockers": [], "pieces": []})


def _write(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(path, payload)


if __name__ == "__main__":
    unittest.main()
