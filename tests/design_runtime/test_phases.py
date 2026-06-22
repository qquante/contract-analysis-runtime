from __future__ import annotations

from pathlib import Path
import json
import os
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
from vassago_contract_runtime import runtime_api
from vassago_contract_runtime.foundry import FoundryRunResult
from vassago_contract_runtime.phases.corpus_motifs import CorpusMotifsAdapter
from vassago_contract_runtime.phases.compile_only import CompileOnlyAdapter
from vassago_contract_runtime.phases.dossier import DossierAdapter
from vassago_contract_runtime.phases.final_report import FinalReportAdapter
from vassago_contract_runtime.phases.intake import IntakeAdapter
from vassago_contract_runtime.phases.onchain_state import OnChainStateAdapter
from vassago_contract_runtime.phases.proof_pieces import ProofPiecesAdapter
from vassago_contract_runtime.phases.runtime_foundry import RuntimeFoundryAdapter
from vassago_contract_runtime.phases.semantic_surface import SemanticSurfaceAdapter
from vassago_contract_runtime.phases.source_truth import SourceTruthAdapter
from vassago_contract_runtime.phases.thesis_acquisition import ThesisAcquisitionAdapter
from vassago_contract_runtime.slither import SlitherAnalysisResult


class _FakeFoundry:
    def compile_harness(self, item):
        return FoundryRunResult(
            status="compile_only_passed",
            provider="fake_foundry",
            target_id=item.target_id,
            metadata={"evidence_status": "compile_only", "no_broadcast_command": True},
        )

    def run_local_fork(self, item):
        return FoundryRunResult(
            status="runtime_completed",
            provider="fake_foundry",
            target_id=item.target_id,
            stdout="[PASS] testUnauthorizedCallerCanInitializeImplementation()",
            metadata={"evidence_status": "runtime_local", "no_broadcast_command": True},
        )


class _FakeSlither:
    def __init__(self) -> None:
        self.calls = []

    def analyze(self, item):
        self.calls.append(item)
        return SlitherAnalysisResult(
            status="completed",
            provider="fake_slither_ir",
            target_id=item.target_id,
            ir={
                "status": "completed",
                "functions": [
                    {
                        "name": "initialize",
                        "signature": "initialize()",
                        "modifiers": [],
                        "state_writes": ["owner"],
                        "internal_calls": [],
                        "external_calls": [],
                        "source_excerpt": "function initialize() external { owner = msg.sender; }",
                    }
                ],
            },
            metadata={"evidence_status": "static_only"},
        )


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

    def test_dossier_selects_target_contract_source_file_from_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source_fixture = Path(tmp) / "source.json"
            source_fixture.write_text(
                json.dumps(
                    {
                        "targets": [
                            {
                                "chain": "eth",
                                "address": "0x1111111111111111111111111111111111111111",
                                "status": "resolved",
                                "provider": "fixture",
                                "abi": [],
                                "source_files": {
                                    "@openzeppelin/Context.sol": "abstract contract Context {}",
                                    "lib/v4-core/lib/solmate/src/auth/Owned.sol": "contract Owned {}",
                                    "src/pkgs/universal-router/lib/v4-periphery/src/libraries/Actions.sol": "library Actions {}",
                                    "src/pkgs/permit2/src/interfaces/IPermit2.sol": "interface IPermit2 {}",
                                    "contracts/Target.sol": "contract Target { function run() external {} }",
                                },
                                "compiler": {"language": "Solidity", "version": "v0.8.20"},
                                "metadata": {"contract_name": "Target"},
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            design = load_design(Path("designs") / "sc01-access" / "design.yaml")
            target = ContractTarget("eth", "0x1111111111111111111111111111111111111111")
            adapters = {
                "00_intake": IntakeAdapter(),
                "01_dossier": DossierAdapter(FixtureSourceResolver.from_file(source_fixture)),
            }

            run_design(design, [target], Path(tmp) / "run", adapters, RunOptions(resume=True))

            target_dir = Path(tmp) / "run" / "targets" / target.target_id / "phases"
            compile_context = json.loads((target_dir / "01_dossier" / "compile-context.json").read_text())
            self.assertEqual(compile_context["selected_source_file"], "contracts/Target.sol")
            self.assertEqual(compile_context["target_contract"], "Target")
            self.assertIn("solmate/=lib/v4-core/lib/solmate/", compile_context["solc_remaps"])
            self.assertIn("permit2/=src/pkgs/permit2/", compile_context["solc_remaps"])
            self.assertIn(
                "@uniswap/v4-periphery/=src/pkgs/universal-router/lib/v4-periphery/",
                compile_context["solc_remaps"],
            )

    def test_proxy_dossier_indexes_related_implementation_functions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source_fixture = Path(tmp) / "source.json"
            source_fixture.write_text(
                json.dumps(
                    {
                        "targets": [
                            {
                                "chain": "eth",
                                "address": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                                "status": "resolved",
                                "provider": "fixture",
                                "abi": [{"type": "fallback", "stateMutability": "payable"}],
                                "source_files": {"Proxy.sol": "contract Proxy { fallback() external payable {} }"},
                                "compiler": {"language": "Solidity", "version": "v0.8.20"},
                                "metadata": {"contract_name": "Proxy"},
                                "proxy_context": {
                                    "proxy": "1",
                                    "implementation": "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                                },
                            },
                            {
                                "chain": "eth",
                                "address": "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                                "status": "resolved",
                                "provider": "fixture",
                                "abi": [
                                    {
                                        "type": "function",
                                        "name": "initialize",
                                        "inputs": [],
                                        "outputs": [],
                                        "stateMutability": "nonpayable",
                                    }
                                ],
                                "source_files": {
                                    "Implementation.sol": "contract Implementation { function initialize() external {} }"
                                },
                                "compiler": {"language": "Solidity", "version": "v0.8.20"},
                                "metadata": {"contract_name": "Implementation"},
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )
            design = load_design(Path("designs") / "sc01-access" / "design.yaml")
            target = ContractTarget("eth", "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
            adapters = {
                "00_intake": IntakeAdapter(),
                "01_dossier": DossierAdapter(FixtureSourceResolver.from_file(source_fixture)),
                "02_semantic_surface": SemanticSurfaceAdapter(),
            }

            run_design(design, [target], Path(tmp) / "run", adapters, RunOptions(resume=True))

            target_dir = Path(tmp) / "run" / "targets" / target.target_id / "phases"
            function_index = json.loads((target_dir / "01_dossier" / "function-index.json").read_text())
            surface = json.loads((target_dir / "02_semantic_surface" / "access-surface.json").read_text())
            initialize_index = next(item for item in function_index["functions"] if item["name"] == "initialize")
            initialize_surface = next(item for item in surface["functions"] if item["name"] == "initialize")
            self.assertEqual(initialize_index["source_relation"], "proxy_implementation")
            self.assertEqual(initialize_index["execution_context"], "proxy_delegatecall")
            self.assertEqual(initialize_surface["source_status"], "found")
            self.assertEqual(initialize_surface["source_relation"], "proxy_implementation")

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

    def test_intake_dossier_semantic_corpus_and_thesis_use_local_fixture_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            design = load_design(Path("designs") / "sc01-access" / "design.yaml")
            target = ContractTarget("eth", "0x1111111111111111111111111111111111111111")
            adapters = {
                "00_intake": IntakeAdapter(),
                "01_dossier": DossierAdapter(FixtureSourceResolver.from_file("tests/fixtures/source_fixture.json")),
                "02_semantic_surface": SemanticSurfaceAdapter(),
                "03_corpus_motifs": CorpusMotifsAdapter.from_design_dir("designs/sc01-access"),
                "04_thesis_acquisition": ThesisAcquisitionAdapter(),
                "05_source_truth": SourceTruthAdapter(),
                "06_onchain_state": OnChainStateAdapter(),
                "07_proof_pieces": ProofPiecesAdapter(),
                "08_compile_only": CompileOnlyAdapter(),
                "09_runtime_foundry": DryRunPhaseAdapter(),
                "10_final_report": FinalReportAdapter(),
            }

            result = run_design(design, [target], Path(tmp) / "run", adapters, RunOptions(resume=True))

            self.assertEqual(result.status, "completed")
            target_dir = Path(tmp) / "run" / "targets" / target.target_id / "phases"
            function_index = json.loads((target_dir / "01_dossier" / "function-index.json").read_text())
            surface = json.loads((target_dir / "02_semantic_surface" / "access-surface.json").read_text())
            candidates = json.loads((target_dir / "03_corpus_motifs" / "sc01-thesis-candidates.json").read_text())
            queue = json.loads((target_dir / "04_thesis_acquisition" / "sc01-thesis-queue.json").read_text())
            source_truth = json.loads((target_dir / "05_source_truth" / "sc01-source-truth.json").read_text())
            admin_state = json.loads((target_dir / "06_onchain_state" / "admin-state.json").read_text())
            runtime_ready = json.loads((target_dir / "07_proof_pieces" / "sc01-runtime-ready.json").read_text())
            compile_result = json.loads((target_dir / "08_compile_only" / "compile-result.json").read_text())
            final_report = json.loads((target_dir / "10_final_report" / "sc01-final-report.json").read_text())
            self.assertEqual(function_index["function_count"], 2)
            self.assertEqual(surface["status"], "completed")
            self.assertGreaterEqual(candidates["candidate_count"], 1)
            self.assertIn("uups_weak_auth", {item["thesis_id"] for item in candidates["candidates"]})
            self.assertGreaterEqual(queue["queue_count"], 1)
            self.assertEqual(source_truth["source_truth_verified_count"], 0)
            self.assertEqual(admin_state["status"], "needs_provider")
            self.assertEqual(runtime_ready["runtime_ready_count"], 0)
            self.assertEqual(runtime_ready["foundry_allowed"], False)
            self.assertEqual(compile_result["status"], "compile_skipped_not_ready")
            self.assertEqual(final_report["final_status"], "blocked_no_runtime_ready")

    def test_semantic_surface_prefers_slither_ir_when_compile_context_is_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            design = load_design(Path("designs") / "sc01-access" / "design.yaml")
            target = ContractTarget("eth", "0x2222222222222222222222222222222222222222")
            slither = _FakeSlither()
            adapters = {
                "00_intake": IntakeAdapter(),
                "01_dossier": DossierAdapter(FixtureSourceResolver.from_file("tests/fixtures/source_fixture_positive.json")),
                "02_semantic_surface": SemanticSurfaceAdapter(slither),
            }

            run_design(design, [target], Path(tmp) / "run", adapters, RunOptions(resume=True))

            target_dir = Path(tmp) / "run" / "targets" / target.target_id / "phases"
            compile_context = json.loads((target_dir / "01_dossier" / "compile-context.json").read_text())
            surface = json.loads((target_dir / "02_semantic_surface" / "access-surface.json").read_text())
            initialize = next(item for item in surface["functions"] if item["signature"] == "initialize()")
            self.assertEqual(compile_context["status"], "available")
            self.assertEqual(compile_context["solc_version_selection"]["requested_version"], "0.8.20")
            self.assertEqual(slither.calls[0].compile_context["status"], "available")
            self.assertEqual(surface["slither"]["status"], "completed")
            self.assertEqual(surface["slither"]["provider"], "fake_slither_ir")
            self.assertEqual(initialize["extraction_source"], "slither_ir")
            self.assertEqual(initialize["confidence"], "high")
            self.assertIn("owner", initialize["state_write_signals"])
            self.assertIn("owner_check", initialize["guard_signals"])

    def test_bootstrap_without_source_fixture_uses_explorer_source_resolver_with_cache(self) -> None:
        design = load_design(Path("designs") / "sc01-access" / "design.yaml")
        created: list[Path | None] = []

        class FakeEtherscanAdapter:
            def __init__(self, *args, cache_dir=None, **kwargs) -> None:
                created.append(Path(cache_dir) if cache_dir else None)

        original = runtime_api.EtherscanV2ExplorerAdapter
        try:
            runtime_api.EtherscanV2ExplorerAdapter = FakeEtherscanAdapter
            adapters = runtime_api.adapters_for(
                design,
                dry_run=False,
                bootstrap=True,
                source_fixture=None,
                source_cache_dir="runs/cache-test",
                design_dir=Path("designs") / "sc01-access",
            )
        finally:
            runtime_api.EtherscanV2ExplorerAdapter = original

        self.assertEqual(created, [Path("runs/cache-test")])
        self.assertEqual(adapters["01_dossier"].source_resolver.explorer.__class__.__name__, "FakeEtherscanAdapter")

    def test_positive_fixture_reaches_runtime_with_authorization(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            design = load_design(Path("designs") / "sc01-access" / "design.yaml")
            target = ContractTarget("eth", "0x2222222222222222222222222222222222222222")
            foundry = _FakeFoundry()
            adapters = {
                "00_intake": IntakeAdapter(),
                "01_dossier": DossierAdapter(FixtureSourceResolver.from_file("tests/fixtures/source_fixture_positive.json")),
                "02_semantic_surface": SemanticSurfaceAdapter(),
                "03_corpus_motifs": CorpusMotifsAdapter.from_design_dir("designs/sc01-access"),
                "04_thesis_acquisition": ThesisAcquisitionAdapter(),
                "05_source_truth": SourceTruthAdapter(),
                "06_onchain_state": OnChainStateAdapter(),
                "07_proof_pieces": ProofPiecesAdapter(),
                "08_compile_only": CompileOnlyAdapter(foundry),
                "09_runtime_foundry": RuntimeFoundryAdapter(foundry, runtime_authorized=True),
                "10_final_report": FinalReportAdapter(),
            }

            result = run_design(design, [target], Path(tmp) / "run", adapters, RunOptions(resume=True))

            self.assertEqual(result.status, "completed")
            target_dir = Path(tmp) / "run" / "targets" / target.target_id / "phases"
            source_truth = json.loads((target_dir / "05_source_truth" / "sc01-source-truth.json").read_text())
            runtime_ready = json.loads((target_dir / "07_proof_pieces" / "sc01-runtime-ready.json").read_text())
            compile_result = json.loads((target_dir / "08_compile_only" / "compile-result.json").read_text())
            runtime_result = json.loads((target_dir / "09_runtime_foundry" / "foundry-runtime-result.json").read_text())
            assertion = json.loads((target_dir / "09_runtime_foundry" / "assertion-result.json").read_text())
            final_report = json.loads((target_dir / "10_final_report" / "sc01-final-report.json").read_text())
            self.assertEqual(source_truth["source_truth_verified_count"], 1)
            self.assertEqual(runtime_ready["runtime_ready_count"], 1)
            self.assertEqual(runtime_ready["foundry_allowed"], True)
            self.assertEqual(compile_result["status"], "compile_only_passed")
            self.assertEqual(runtime_result["status"], "runtime_completed")
            self.assertEqual(assertion["status"], "passed")
            self.assertEqual(assertion["predicate"], source_truth["reviews"][0]["explicit_predicate"])
            self.assertEqual(assertion["measured_delta"], source_truth["reviews"][0]["measurable_delta"])
            self.assertEqual(final_report["final_status"], "runtime_completed")
            self.assertEqual(final_report["evidence_status"], "runtime_local")

    def test_wormhole_fixture_reaches_runtime_gate_with_specific_harness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source_fixture = Path(tmp) / "wormhole-source.json"
            source_fixture.write_text(json.dumps(_wormhole_source_fixture()), encoding="utf-8")
            design = load_design(Path("designs") / "sc01-access" / "design.yaml")
            target = ContractTarget("eth", "0x98f3c9e6E3fAce36bAAd05FE09d375Ef1464288B")
            foundry = _FakeFoundry()
            adapters = {
                "00_intake": IntakeAdapter(),
                "01_dossier": DossierAdapter(FixtureSourceResolver.from_file(source_fixture)),
                "02_semantic_surface": SemanticSurfaceAdapter(),
                "03_corpus_motifs": CorpusMotifsAdapter.from_design_dir("designs/sc01-access"),
                "04_thesis_acquisition": ThesisAcquisitionAdapter(),
                "05_source_truth": SourceTruthAdapter(),
                "06_onchain_state": OnChainStateAdapter(),
                "07_proof_pieces": ProofPiecesAdapter(),
                "08_compile_only": CompileOnlyAdapter(foundry),
                "09_runtime_foundry": RuntimeFoundryAdapter(foundry, runtime_authorized=True),
                "10_final_report": FinalReportAdapter(),
            }

            old_rpc = os.environ.get("VASSAGO_FORK_RPC_URL")
            os.environ["VASSAGO_FORK_RPC_URL"] = "http://127.0.0.1:8545"
            try:
                result = run_design(design, [target], Path(tmp) / "run", adapters, RunOptions(resume=True))
            finally:
                if old_rpc is None:
                    os.environ.pop("VASSAGO_FORK_RPC_URL", None)
                else:
                    os.environ["VASSAGO_FORK_RPC_URL"] = old_rpc

            self.assertEqual(result.status, "completed")
            target_dir = Path(tmp) / "run" / "targets" / target.target_id / "phases"
            source_truth = json.loads((target_dir / "05_source_truth" / "sc01-source-truth.json").read_text())
            runtime_ready = json.loads((target_dir / "07_proof_pieces" / "sc01-runtime-ready.json").read_text())
            harness = (target_dir / "08_compile_only" / "VassagoSC01Harness.t.sol").read_text()
            runtime_result = json.loads((target_dir / "09_runtime_foundry" / "foundry-runtime-result.json").read_text())
            self.assertEqual(source_truth["source_truth_verified_count"], 1)
            self.assertEqual(source_truth["reviews"][0]["runtime_runner"], "wormhole_implementation_runtime")
            self.assertEqual(runtime_ready["foundry_allowed"], True)
            self.assertIn("testWormholeImplementationInitializerReplayExecutesMaliciousDelegatecall", harness)
            self.assertIn("MALICIOUS_MARKER_SLOT", harness)
            self.assertEqual(runtime_result["status"], "runtime_completed")

    def test_nomad_fixture_reaches_runtime_gate_with_specific_harness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source_fixture = Path(tmp) / "nomad-source.json"
            source_fixture.write_text(json.dumps(_nomad_source_fixture()), encoding="utf-8")
            design = load_design(Path("designs") / "sc01-access" / "design.yaml")
            target = ContractTarget("eth", "0x5d94309e5a0090b165fa4181519701637b6daeba")
            foundry = _FakeFoundry()
            adapters = {
                "00_intake": IntakeAdapter(),
                "01_dossier": DossierAdapter(FixtureSourceResolver.from_file(source_fixture)),
                "02_semantic_surface": SemanticSurfaceAdapter(),
                "03_corpus_motifs": CorpusMotifsAdapter.from_design_dir("designs/sc01-access"),
                "04_thesis_acquisition": ThesisAcquisitionAdapter(),
                "05_source_truth": SourceTruthAdapter(),
                "06_onchain_state": OnChainStateAdapter(),
                "07_proof_pieces": ProofPiecesAdapter(),
                "08_compile_only": CompileOnlyAdapter(foundry),
                "09_runtime_foundry": RuntimeFoundryAdapter(foundry, runtime_authorized=True),
                "10_final_report": FinalReportAdapter(),
            }

            old_rpc = os.environ.get("VASSAGO_FORK_RPC_URL")
            os.environ["VASSAGO_FORK_RPC_URL"] = "http://127.0.0.1:8545"
            try:
                result = run_design(design, [target], Path(tmp) / "run", adapters, RunOptions(resume=True))
            finally:
                if old_rpc is None:
                    os.environ.pop("VASSAGO_FORK_RPC_URL", None)
                else:
                    os.environ["VASSAGO_FORK_RPC_URL"] = old_rpc

            self.assertEqual(result.status, "completed")
            target_dir = Path(tmp) / "run" / "targets" / target.target_id / "phases"
            source_truth = json.loads((target_dir / "05_source_truth" / "sc01-source-truth.json").read_text())
            nomad_analysis = json.loads((target_dir / "05_source_truth" / "nomad-root-proof-analysis.json").read_text())
            bridge_state = json.loads((target_dir / "06_onchain_state" / "bridge-state-review.json").read_text())
            admin_state = json.loads((target_dir / "06_onchain_state" / "admin-state.json").read_text())
            runtime_ready = json.loads((target_dir / "07_proof_pieces" / "sc01-runtime-ready.json").read_text())
            harness = (target_dir / "08_compile_only" / "VassagoSC01Harness.t.sol").read_text()
            runtime_result = json.loads((target_dir / "09_runtime_foundry" / "foundry-runtime-result.json").read_text())
            self.assertEqual(source_truth["source_truth_verified_count"], 1)
            self.assertIn("bridge_root_proof_validation", {item["thesis_id"] for item in source_truth["reviews"]})
            nomad_review = next(item for item in source_truth["reviews"] if item["thesis_id"] == "bridge_root_proof_validation")
            self.assertEqual(nomad_review["runtime_runner"], "nomad_bridge_root_proof_runtime")
            self.assertEqual(nomad_analysis["status"], "historical_runtime_ready")
            self.assertEqual(bridge_state["status"], "historical_fork_state_ready_current_live_not_claimed")
            self.assertEqual(admin_state["status"], "protocol_specific_admin_state_not_required")
            self.assertFalse(bridge_state["current_state_review"]["live_claim_allowed"])
            self.assertEqual(runtime_ready["foundry_allowed"], True)
            self.assertIn("testNomadProcessesUnprovenForgedMessageOnHistoricalFork", harness)
            self.assertIn("VassagoNomadReceiver", harness)
            self.assertEqual(runtime_result["status"], "runtime_completed")

    def test_negative_public_accounting_fixture_rejects_initialize_name_noise(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            design = load_design(Path("designs") / "sc01-access" / "design.yaml")
            target = ContractTarget("eth", "0x3333333333333333333333333333333333333333")
            adapters = {
                "00_intake": IntakeAdapter(),
                "01_dossier": DossierAdapter(FixtureSourceResolver.from_file("tests/fixtures/source_fixture_negative.json")),
                "02_semantic_surface": SemanticSurfaceAdapter(),
                "03_corpus_motifs": CorpusMotifsAdapter.from_design_dir("designs/sc01-access"),
                "04_thesis_acquisition": ThesisAcquisitionAdapter(),
                "05_source_truth": SourceTruthAdapter(),
                "06_onchain_state": OnChainStateAdapter(),
                "07_proof_pieces": ProofPiecesAdapter(),
                "08_compile_only": CompileOnlyAdapter(_FakeFoundry()),
                "09_runtime_foundry": RuntimeFoundryAdapter(_FakeFoundry(), runtime_authorized=True),
                "10_final_report": FinalReportAdapter(),
            }

            result = run_design(design, [target], Path(tmp) / "run", adapters, RunOptions(resume=True))

            self.assertEqual(result.status, "completed")
            target_dir = Path(tmp) / "run" / "targets" / target.target_id / "phases"
            candidates = json.loads((target_dir / "03_corpus_motifs" / "sc01-thesis-candidates.json").read_text())
            source_truth = json.loads((target_dir / "05_source_truth" / "sc01-source-truth.json").read_text())
            runtime_ready = json.loads((target_dir / "07_proof_pieces" / "sc01-runtime-ready.json").read_text())
            final_report = json.loads((target_dir / "10_final_report" / "sc01-final-report.json").read_text())
            self.assertGreaterEqual(candidates["candidate_count"], 1)
            self.assertEqual(source_truth["status"], "source_truth_rejected")
            self.assertEqual(source_truth["source_truth_verified_count"], 0)
            self.assertGreaterEqual(source_truth["source_truth_rejected_count"], 1)
            self.assertEqual(source_truth["reviews"][0]["status"], "source_truth_rejected")
            self.assertEqual(source_truth["reviews"][0]["classification"], "caller_funded_accounting")
            self.assertEqual(runtime_ready["foundry_allowed"], False)
            self.assertEqual(final_report["final_status"], "blocked_no_runtime_ready")

    def test_adversarial_fixture_suite_routes_without_false_foundry_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            design = load_design(Path("designs") / "sc01-access" / "design.yaml")
            targets = [
                ContractTarget("eth", "0x4444444444444444444444444444444444444444"),
                ContractTarget("eth", "0x5555555555555555555555555555555555555555"),
                ContractTarget("eth", "0x6666666666666666666666666666666666666666"),
                ContractTarget("eth", "0x7777777777777777777777777777777777777777"),
            ]
            adapters = {
                "00_intake": IntakeAdapter(),
                "01_dossier": DossierAdapter(FixtureSourceResolver.from_file("tests/fixtures/source_fixture_adversarial.json")),
                "02_semantic_surface": SemanticSurfaceAdapter(),
                "03_corpus_motifs": CorpusMotifsAdapter.from_design_dir("designs/sc01-access"),
                "04_thesis_acquisition": ThesisAcquisitionAdapter(),
                "05_source_truth": SourceTruthAdapter(),
                "06_onchain_state": OnChainStateAdapter(),
                "07_proof_pieces": ProofPiecesAdapter(),
                "08_compile_only": CompileOnlyAdapter(_FakeFoundry()),
                "09_runtime_foundry": RuntimeFoundryAdapter(_FakeFoundry(), runtime_authorized=True),
                "10_final_report": FinalReportAdapter(),
            }

            result = run_design(design, targets, Path(tmp) / "run", adapters, RunOptions(resume=True))

            self.assertEqual(result.status, "completed")
            by_address = _phase_dirs_by_address(Path(tmp) / "run")

            disabled = by_address["0x4444444444444444444444444444444444444444"]
            disabled_source_truth = _read_phase(disabled, "05_source_truth", "sc01-source-truth.json")
            disabled_final = _read_phase(disabled, "10_final_report", "sc01-final-report.json")
            self.assertEqual(disabled_source_truth["source_truth_verified_count"], 0)
            self.assertEqual(disabled_final["foundry_allowed"], False)

            tx_origin = by_address["0x5555555555555555555555555555555555555555"]
            tx_queue = _read_phase(tx_origin, "04_thesis_acquisition", "sc01-thesis-queue.json")
            tx_guard = _read_phase(tx_origin, "02_semantic_surface", "guard-map.json")
            tx_final = _read_phase(tx_origin, "10_final_report", "sc01-final-report.json")
            self.assertIn("tx_origin_authorization", {item["thesis_id"] for item in tx_queue["queue"]})
            self.assertIn("tx_origin_authorization", {item["guard_class"] for item in tx_guard["guards"]})
            self.assertEqual(tx_final["foundry_allowed"], False)

            role_admin = by_address["0x6666666666666666666666666666666666666666"]
            role_queue = _read_phase(role_admin, "04_thesis_acquisition", "sc01-thesis-queue.json")
            role_final = _read_phase(role_admin, "10_final_report", "sc01-final-report.json")
            self.assertIn("role_admin_escalation", {item["thesis_id"] for item in role_queue["queue"]})
            self.assertEqual(role_final["foundry_allowed"], False)

            lifecycle = by_address["0x7777777777777777777777777777777777777777"]
            lifecycle_source_truth = _read_phase(lifecycle, "05_source_truth", "sc01-source-truth.json")
            lifecycle_final = _read_phase(lifecycle, "10_final_report", "sc01-final-report.json")
            self.assertEqual(lifecycle_source_truth["status"], "source_truth_rejected")
            self.assertEqual(lifecycle_source_truth["reviews"][0]["classification"], "public_lifecycle")
            self.assertEqual(lifecycle_final["foundry_allowed"], False)

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
            queue = json.loads(
                (run_dir / "targets" / target_id / "phases" / "04_thesis_acquisition" / "sc01-thesis-queue.json").read_text()
            )
            runtime_ready = json.loads(
                (run_dir / "targets" / target_id / "phases" / "07_proof_pieces" / "sc01-runtime-ready.json").read_text()
            )
            compile_result = json.loads(
                (run_dir / "targets" / target_id / "phases" / "08_compile_only" / "compile-result.json").read_text()
            )
            final_report = json.loads(
                (run_dir / "targets" / target_id / "phases" / "10_final_report" / "sc01-final-report.json").read_text()
            )
            source_truth = json.loads(
                (run_dir / "targets" / target_id / "phases" / "05_source_truth" / "sc01-source-truth.json").read_text()
            )
            self.assertEqual(dossier["status"], "skeleton")
            self.assertGreaterEqual(corpus["candidate_count"], 1)
            self.assertEqual(later["status"], "completed")
            self.assertGreaterEqual(queue["queue_count"], 1)
            self.assertEqual(source_truth["status"], "blocked")
            self.assertEqual(runtime_ready["status"], "blocked")
            self.assertEqual(runtime_ready["runtime_ready_count"], 0)
            self.assertEqual(compile_result["status"], "compile_skipped_not_ready")
            self.assertEqual(final_report["final_status"], "blocked_no_runtime_ready")

def _phase_dirs_by_address(run_dir: Path) -> dict[str, Path]:
    by_address = {}
    for target_dir in (run_dir / "targets").iterdir():
        manifest = json.loads((target_dir / "phases" / "00_intake" / "target-manifest.json").read_text())
        by_address[str(manifest["target"]["address"]).lower()] = target_dir / "phases"
    return by_address


def _read_phase(phases_dir: Path, phase_id: str, artifact: str) -> dict:
    return json.loads((phases_dir / phase_id / artifact).read_text())


def _wormhole_source_fixture() -> dict:
    return {
        "targets": [
            {
                "chain": "eth",
                "address": "0x98f3c9e6E3fAce36bAAd05FE09d375Ef1464288B",
                "status": "resolved",
                "provider": "fixture",
                "abi": [{"type": "fallback", "stateMutability": "payable"}],
                "source_files": {"WormholeProxy.sol": "contract WormholeProxy { fallback() external payable {} }"},
                "compiler": {"language": "Solidity", "version": "v0.8.24"},
                "metadata": {"contract_name": "WormholeProxy"},
                "proxy_context": {"proxy": "1", "implementation": "0x3333333333333333333333333333333333333333"},
            },
            {
                "chain": "eth",
                "address": "0x3333333333333333333333333333333333333333",
                "status": "resolved",
                "provider": "fixture",
                "abi": [
                    {"type": "function", "name": "initialize", "inputs": [], "outputs": [], "stateMutability": "nonpayable"},
                    {
                        "type": "function",
                        "name": "isInitialized",
                        "inputs": [{"type": "address"}],
                        "outputs": [{"type": "bool"}],
                        "stateMutability": "view",
                    },
                    {
                        "type": "function",
                        "name": "getGuardianSet",
                        "inputs": [{"type": "uint32"}],
                        "outputs": [],
                        "stateMutability": "view",
                    },
                    {
                        "type": "function",
                        "name": "submitContractUpgrade",
                        "inputs": [{"type": "bytes"}],
                        "outputs": [],
                        "stateMutability": "nonpayable",
                    },
                ],
                "source_files": {
                    "Implementation.sol": """
                    contract Implementation {
                        modifier initializer() {
                            address implementation = ERC1967Upgrade._getImplementation();
                            require(!isInitialized(implementation), "already initialized");
                            setInitialized(implementation);
                            _;
                        }
                        function initialize() initializer public {}
                        function isInitialized(address) public view returns (bool) {}
                        function getGuardianSet(uint32) public view {}
                        function submitContractUpgrade(bytes memory _vm) public {
                            Structs.VM memory vm = parseVM(_vm);
                            verifyGovernanceVM(vm);
                            GovernanceStructs.ContractUpgrade memory upgrade = parseContractUpgrade(vm.payload);
                            upgradeImplementation(upgrade.newContract);
                        }
                        function upgradeImplementation(address newImplementation) internal {
                            newImplementation.delegatecall(abi.encodeWithSignature("initialize()"));
                        }
                        function verifyGovernanceVM(Structs.VM memory vm) internal view {}
                        string guardianSet;
                    }
                    """,
                },
                "compiler": {"language": "Solidity", "version": "v0.8.24"},
                "metadata": {"contract_name": "Implementation"},
            },
        ]
    }


def _nomad_source_fixture() -> dict:
    replica_source = """
    contract Replica {
        mapping(bytes32 => uint256) public confirmAt;
        mapping(bytes32 => bytes32) public messages;
        bytes32 public constant LEGACY_STATUS_PROCESSED = bytes32(uint256(2));
        function localDomain() public view returns (uint32) {}
        function process(bytes memory _message) public returns (bool) {
            bytes32 _messageHash = keccak256(_message);
            require(acceptableRoot(messages[_messageHash]), "!proven");
            messages[_messageHash] = LEGACY_STATUS_PROCESSED;
            return true;
        }
        function prove(bytes32 _leaf, bytes32[32] calldata _proof, uint256 _index) public returns (bool) {}
        function proveAndProcess(bytes memory _message, bytes32[32] calldata _proof, uint256 _index) external {
            bytes32 _messageHash = keccak256(_message);
            require(acceptableRoot(messages[_messageHash]) || prove(_messageHash, _proof, _index), "!prove");
            process(_message);
        }
        function acceptableRoot(bytes32 _root) public view returns (bool) {
            if (_root == LEGACY_STATUS_PROCESSED) return false;
            uint256 _time = confirmAt[_root];
            if (_time == 0) return false;
            return block.timestamp >= _time;
        }
    }
    """
    return {
        "targets": [
            {
                "chain": "eth",
                "address": "0x5d94309e5a0090b165fa4181519701637b6daeba",
                "status": "resolved",
                "provider": "fixture",
                "abi": [{"type": "fallback", "stateMutability": "payable"}],
                "source_files": {"Proxy.sol": "contract UpgradeBeaconProxy { fallback() external payable {} }"},
                "compiler": {"language": "Solidity", "version": "v0.7.6"},
                "metadata": {"contract_name": "UpgradeBeaconProxy"},
                "proxy_context": {"proxy": "1", "implementation": "0xb92336759618f55bd0f8313bd843604592e27bd8"},
            },
            {
                "chain": "eth",
                "address": "0xb92336759618f55bd0f8313bd843604592e27bd8",
                "status": "resolved",
                "provider": "fixture",
                "abi": [
                    {"type": "function", "name": "localDomain", "inputs": [], "outputs": [{"type": "uint32"}], "stateMutability": "view"},
                    {"type": "function", "name": "messages", "inputs": [{"type": "bytes32"}], "outputs": [{"type": "bytes32"}], "stateMutability": "view"},
                    {"type": "function", "name": "acceptableRoot", "inputs": [{"type": "bytes32"}], "outputs": [{"type": "bool"}], "stateMutability": "view"},
                    {"type": "function", "name": "confirmAt", "inputs": [{"type": "bytes32"}], "outputs": [{"type": "uint256"}], "stateMutability": "view"},
                    {"type": "function", "name": "LEGACY_STATUS_PROCESSED", "inputs": [], "outputs": [{"type": "bytes32"}], "stateMutability": "view"},
                    {"type": "function", "name": "process", "inputs": [{"type": "bytes"}], "outputs": [{"type": "bool"}], "stateMutability": "nonpayable"},
                    {"type": "function", "name": "prove", "inputs": [{"type": "bytes32"}, {"type": "bytes32[32]"}, {"type": "uint256"}], "outputs": [{"type": "bool"}], "stateMutability": "nonpayable"},
                    {"type": "function", "name": "proveAndProcess", "inputs": [{"type": "bytes"}, {"type": "bytes32[32]"}, {"type": "uint256"}], "outputs": [], "stateMutability": "nonpayable"},
                ],
                "source_files": {"Replica.sol": replica_source},
                "compiler": {"language": "Solidity", "version": "v0.7.6"},
                "metadata": {"contract_name": "Replica"},
            },
        ]
    }


if __name__ == "__main__":
    unittest.main()
