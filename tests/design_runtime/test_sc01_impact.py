from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from vassago_contract_runtime.artifacts.store import ArtifactStore
from vassago_contract_runtime.sc01_impact import build_sc01_impact_review, write_sc01_impact_review


class SC01ImpactReviewTests(unittest.TestCase):
    def test_audius_impact_review_separates_historical_critical_from_live_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            target_id = "CT-audius"
            _write_minimal_audius_run(run_dir, target_id)

            summary = write_sc01_impact_review(run_dir, target_id)
            review = build_sc01_impact_review(run_dir, target_id)

            self.assertEqual(summary["status"], "completed")
            self.assertEqual(review["summary"]["verdict"], "historical_reproduced_critical")
            self.assertEqual(review["historical_impact"]["severity"], "critical_historical")
            self.assertEqual(review["current_live_risk"]["status"], "not_claimed")
            self.assertTrue(review["local_reproduction"]["no_broadcast"])
            self.assertIn("current-state review", review["current_live_risk"]["reason"])
            self.assertTrue((run_dir / "targets" / target_id / "phases" / "11_impact_review" / "sc01-impact-review.md").is_file())


def _write_minimal_audius_run(run_dir: Path, target_id: str) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run-manifest.json").write_text(json.dumps({"run_id": "RUN-audius-test"}) + "\n", encoding="utf-8")
    store = ArtifactStore(run_dir, "RUN-audius-test")
    store.write_json_artifact(
        target_id,
        "01_dossier",
        "source-manifest.json",
        {
            "target": {"chain": "eth", "address": "0x4deca517d6817b6510798b7328f2314d3003abac"},
            "source_files": {"AudiusProxy.sol": "contract AudiusProxy {}"},
        },
    )
    store.write_json_artifact(
        target_id,
        "05_source_truth",
        "sc01-source-truth.json",
        {
            "status": "source_truth_verified",
            "source_truth_verified_count": 1,
            "reviews": [{"evidence_kind": "proxy_storage_collision_reinitializer", "source_truth_verified": True}],
        },
    )
    store.write_json_artifact(
        target_id,
        "09_runtime_foundry",
        "foundry-runtime-result.json",
        {"status": "runtime_completed", "no_broadcast": True},
    )
    store.write_json_artifact(
        target_id,
        "09_runtime_foundry",
        "assertion-result.json",
        {
            "status": "passed",
            "evidence_status": "runtime_local",
            "predicate": "proxy initialize changes guardian",
            "measured_delta": "guardian changed",
        },
    )
    store.write_json_artifact(
        target_id,
        "10_final_report",
        "sc01-final-report.json",
        {
            "address": "0x4deca517d6817b6510798b7328f2314d3003abac",
            "chain": "eth",
            "runtime_status": "runtime_completed",
            "runtime_ready_count": 1,
            "source_truth_verified_count": 1,
            "final_status": "runtime_completed",
        },
    )


if __name__ == "__main__":
    unittest.main()
