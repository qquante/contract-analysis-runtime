from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from vassago_contract_runtime.historical_corpus import (
    DEFAULT_HISTORICAL_CORPUS,
    build_historical_corpus_report,
    write_historical_blind_targets,
)


class HistoricalCorpusTests(unittest.TestCase):
    def test_manifest_has_100_balanced_cases(self) -> None:
        report = build_historical_corpus_report(DEFAULT_HISTORICAL_CORPUS)

        self.assertEqual(report["status"], "completed")
        self.assertEqual(report["summary"]["case_count"], 100)
        self.assertEqual(report["summary"]["target_count"], 100)
        self.assertEqual(report["summary"]["ready_for_blind_benchmark"], 100)
        self.assertEqual(report["summary"]["duplicate_target_count"], 0)
        self.assertEqual(
            report["summary"]["by_family"],
            {
                "bridge_message_auth": 20,
                "oracle_accounting": 20,
                "proxy_upgrade_signature": 20,
                "reentrancy_token": 20,
                "sc01_access_control": 20,
            },
        )
        self.assertEqual(report["invalid_cases"], [])
        self.assertTrue(all(item["chain"] != "unknown" for item in report["targets"]))

    def test_family_filter_exports_only_blind_targets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "targets.json"

            result = write_historical_blind_targets(
                output,
                DEFAULT_HISTORICAL_CORPUS,
                family="bridge_message_auth",
                limit=3,
            )

            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["target_count"], 3)
            self.assertEqual(len(payload["targets"]), 3)
            self.assertNotIn("hidden_ground_truth", json.dumps(payload))
            self.assertTrue(all(item["metadata"]["family_hint"] == "bridge_message_auth" for item in payload["targets"]))


if __name__ == "__main__":
    unittest.main()
