from __future__ import annotations

from pathlib import Path
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO

from vassago_contract_runtime.cli import main
from vassago_contract_runtime.contracts import ContractTargetRef, FixtureSourceResolver, NullSourceResolver
from vassago_contract_runtime.design_runtime.adapters import DryRunPhaseAdapter
from vassago_contract_runtime.design_runtime.design_loader import load_design
from vassago_contract_runtime.design_runtime.models import ContractTarget, RunOptions
from vassago_contract_runtime.design_runtime.runner import run_design
from vassago_contract_runtime.phases.corpus_motifs import CorpusMotifsAdapter
from vassago_contract_runtime.phases.dossier import DossierAdapter
from vassago_contract_runtime.phases.intake import IntakeAdapter


class BootstrapPhaseTests(unittest.TestCase):
    def test_null_source_resolver_returns_unresolved_skeleton(self) -> None:
        target = ContractTargetRef.from_target(ContractTarget("eth", "0x1111111111111111111111111111111111111111"))

        resolution = NullSourceResolver().resolve(target)

        self.assertEqual(resolution.status, "unresolved")
        self.assertEqual(resolution.provider, "null")
        self.assertEqual(resolution.error["code"], "source_resolver_not_configured")

    def test_fixture_source_resolver_returns_local_abi_and_source(self) -> None:
        target = ContractTargetRef.from_target(ContractTarget("eth", "0x1111111111111111111111111111111111111111"))

        resolution = FixtureSourceResolver.from_file("tests/fixtures/source_fixture.json").resolve(target)

        self.assertEqual(resolution.status, "resolved")
        self.assertEqual(resolution.provider, "fixture")
        self.assertEqual(len(resolution.abi or []), 3)
        self.assertIn("FixtureUUPS.sol", resolution.source_files)

    def test_intake_and_dossier_adapters_write_real_bootstrap_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            design = load_design(Path("designs") / "sc01-access" / "design.yaml")
            target = ContractTarget("eth", "0x1111111111111111111111111111111111111111")
            adapters = {
                "00_intake": IntakeAdapter(),
                "01_dossier": DossierAdapter(),
            }

            result = run_design(design, [target], Path(tmp) / "run", adapters, RunOptions(resume=True))

            self.assertEqual(result.status, "stopped")
            target_dir = Path(tmp) / "run" / "targets" / target.target_id
            target_manifest = json.loads((target_dir / "phases" / "00_intake" / "target-manifest.json").read_text())
            dossier = json.loads((target_dir / "phases" / "01_dossier" / "scan-dossier.json").read_text())
            self.assertEqual(target_manifest["status"], "completed")
            self.assertEqual(dossier["status"], "skeleton")
            self.assertEqual(dossier["source_resolution"]["status"], "unresolved")

    def test_intake_dossier_and_corpus_adapters_use_local_fixture_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            design = load_design(Path("designs") / "sc01-access" / "design.yaml")
            target = ContractTarget("eth", "0x1111111111111111111111111111111111111111")
            adapters = {
                "00_intake": IntakeAdapter(),
                "01_dossier": DossierAdapter(FixtureSourceResolver.from_file("tests/fixtures/source_fixture.json")),
                "02_semantic_surface": DryRunPhaseAdapter(),
                "03_corpus_motifs": CorpusMotifsAdapter.from_design_dir("designs/sc01-access"),
            }

            result = run_design(design, [target], Path(tmp) / "run", adapters, RunOptions(resume=True))

            self.assertEqual(result.status, "stopped")
            target_dir = Path(tmp) / "run" / "targets" / target.target_id / "phases"
            function_index = json.loads((target_dir / "01_dossier" / "function-index.json").read_text())
            candidates = json.loads((target_dir / "03_corpus_motifs" / "sc01-thesis-candidates.json").read_text())
            self.assertEqual(function_index["function_count"], 2)
            self.assertGreaterEqual(candidates["candidate_count"], 1)
            self.assertIn("uups_weak_auth", {item["thesis_id"] for item in candidates["candidates"]})

    def test_cli_bootstrap_adapters_run_bootstrap_phases_and_dry_run_rest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            with redirect_stdout(StringIO()):
                code = main(
                    [
                        "run-design",
                        "--design",
                        "sc01-access",
                        "--targets",
                        "tests/fixtures/targets.json",
                        "--output",
                        str(run_dir),
                        "--source-fixture",
                        "tests/fixtures/source_fixture.json",
                        "--bootstrap-adapters",
                    ]
                )

            self.assertEqual(code, 0)
            manifest = json.loads((run_dir / "run-manifest.json").read_text())
            target_id = manifest["targets"][0]["target_id"]
            dossier = json.loads((run_dir / "targets" / target_id / "phases" / "01_dossier" / "scan-dossier.json").read_text())
            corpus = json.loads(
                (run_dir / "targets" / target_id / "phases" / "03_corpus_motifs" / "sc01-thesis-candidates.json").read_text()
            )
            later = json.loads(
                (run_dir / "targets" / target_id / "phases" / "02_semantic_surface" / "access-surface.json").read_text()
            )
            self.assertEqual(dossier["status"], "skeleton")
            self.assertGreaterEqual(corpus["candidate_count"], 1)
            self.assertEqual(later["status"], "dry_run")


if __name__ == "__main__":
    unittest.main()
