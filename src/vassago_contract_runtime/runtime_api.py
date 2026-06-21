"""Programmatic runtime API shared by CLI and agent tools."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from vassago_contract_runtime.artifacts.store import ArtifactStore
from vassago_contract_runtime.contracts import ExplorerSourceResolver, FixtureSourceResolver, SourceResolver
from vassago_contract_runtime.design_runtime.adapters import dry_run_adapters
from vassago_contract_runtime.design_runtime.design_loader import load_design
from vassago_contract_runtime.design_runtime.manifest import load_run_manifest
from vassago_contract_runtime.design_runtime.models import ContractTarget, RunOptions
from vassago_contract_runtime.design_runtime.runner import resume_design, run_design
from vassago_contract_runtime.explorer import EtherscanV2ExplorerAdapter
from vassago_contract_runtime.phases.compile_only import CompileOnlyAdapter
from vassago_contract_runtime.phases.corpus_motifs import CorpusMotifsAdapter
from vassago_contract_runtime.phases.dossier import DossierAdapter
from vassago_contract_runtime.phases.final_report import FinalReportAdapter
from vassago_contract_runtime.phases.intake import IntakeAdapter
from vassago_contract_runtime.phases.onchain_state import OnChainStateAdapter
from vassago_contract_runtime.phases.proof_pieces import ProofPiecesAdapter
from vassago_contract_runtime.phases.runtime_foundry import RuntimeFoundryAdapter
from vassago_contract_runtime.phases.semantic_surface import SemanticSurfaceAdapter
from vassago_contract_runtime.phases.source_truth import SourceTruthAdapter
from vassago_contract_runtime.phases.thesis_acquisition import ThesisAcquisitionAdapter
from vassago_contract_runtime.foundry import SubprocessFoundryAdapter
from vassago_contract_runtime.slither import PythonSlitherAdapter


def run_design_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    design_path = resolve_design_path(str(payload["design"]))
    design = load_design(design_path)
    targets = load_targets_payload(payload.get("targets"), payload.get("targets_path"))
    dry_run = bool(payload.get("dry_run", False))
    bootstrap = bool(payload.get("bootstrap_adapters", False))
    if not dry_run and not bootstrap:
        raise ValueError("Use dry_run=true or bootstrap_adapters=true until all real phase adapters exist.")
    result = run_design(
        design,
        targets,
        payload["output"],
        adapters_for(
            design,
            dry_run=dry_run,
            bootstrap=bootstrap,
            source_fixture=payload.get("source_fixture"),
            source_cache_dir=payload.get("source_cache_dir") or str(Path(payload["output"]) / "_cache" / "etherscan-v2"),
            design_dir=design_path.parent,
            runtime_authorized=bool(payload.get("runtime_authorized", False)),
            allow_solc_install=bool(payload.get("allow_solc_install", False)),
        ),
        RunOptions(resume=bool(payload.get("resume", True)), dry_run=dry_run),
    )
    return run_result_payload(result)


def resume_design_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    run_dir = payload["run"]
    manifest = load_run_manifest(run_dir)
    design = load_design_from_manifest(manifest)
    dry_run = bool(payload.get("dry_run", False))
    bootstrap = bool(payload.get("bootstrap_adapters", False))
    if not dry_run and not bootstrap:
        raise ValueError("Use dry_run=true or bootstrap_adapters=true until all real phase adapters exist.")
    result = resume_design(
        run_dir,
        adapters_for(
            design,
            dry_run=dry_run,
            bootstrap=bootstrap,
            source_fixture=payload.get("source_fixture"),
            source_cache_dir=payload.get("source_cache_dir") or str(Path(run_dir) / "_cache" / "etherscan-v2"),
            design_dir=Path("designs") / design.design_id,
            runtime_authorized=bool(payload.get("runtime_authorized", False)),
            allow_solc_install=bool(payload.get("allow_solc_install", False)),
        ),
        RunOptions(resume=True, dry_run=dry_run),
    )
    return run_result_payload(result)


def read_artifact_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    manifest = load_run_manifest(payload["run"])
    store = ArtifactStore(payload["run"], manifest["run_id"])
    artifact = store.read_artifact(payload["uri"])
    return {
        "status": "completed",
        "run_id": manifest["run_id"],
        "uri": payload["uri"],
        "artifact": artifact,
        "artifact_type": "text" if isinstance(artifact, str) else "json",
    }


def resolve_design_path(value: str) -> Path:
    path = Path(value)
    if path.is_file():
        return path
    return Path("designs") / value / "design.yaml"


def load_design_from_manifest(manifest: dict[str, Any]) -> Any:
    from vassago_contract_runtime.design_runtime.models import DesignSpec

    return DesignSpec.from_json(manifest["design"])


def adapters_for(
    design: Any,
    *,
    dry_run: bool,
    bootstrap: bool,
    source_fixture: str | None = None,
    source_cache_dir: str | None = None,
    design_dir: Path | None = None,
    runtime_authorized: bool = False,
    allow_solc_install: bool = False,
) -> dict[str, Any]:
    adapters = dry_run_adapters([phase.phase_id for phase in design.phases])
    if bootstrap and not dry_run:
        source_resolver = _source_resolver(source_fixture=source_fixture, source_cache_dir=source_cache_dir)
        adapters["00_intake"] = IntakeAdapter()
        adapters["01_dossier"] = DossierAdapter(source_resolver)
        adapters["02_semantic_surface"] = SemanticSurfaceAdapter(PythonSlitherAdapter(allow_solc_install=allow_solc_install))
        adapters["03_corpus_motifs"] = CorpusMotifsAdapter.from_design_dir(str(design_dir or Path("designs") / design.design_id))
        adapters["04_thesis_acquisition"] = ThesisAcquisitionAdapter()
        adapters["05_source_truth"] = SourceTruthAdapter()
        adapters["06_onchain_state"] = OnChainStateAdapter()
        adapters["07_proof_pieces"] = ProofPiecesAdapter()
        foundry = SubprocessFoundryAdapter()
        adapters["08_compile_only"] = CompileOnlyAdapter(foundry)
        adapters["09_runtime_foundry"] = RuntimeFoundryAdapter(foundry, runtime_authorized=runtime_authorized)
        adapters["10_final_report"] = FinalReportAdapter()
    return adapters


def _source_resolver(*, source_fixture: str | None, source_cache_dir: str | None) -> SourceResolver:
    if source_fixture:
        return FixtureSourceResolver.from_file(source_fixture)
    return ExplorerSourceResolver(EtherscanV2ExplorerAdapter(cache_dir=source_cache_dir))


def load_targets_payload(targets: Any, targets_path: str | None = None) -> list[ContractTarget]:
    if targets_path:
        payload = json.loads(Path(targets_path).read_text(encoding="utf-8"))
        records = payload.get("targets", []) if isinstance(payload, dict) else payload
    else:
        records = targets
    if not isinstance(records, list) or not records:
        raise ValueError("Targets must be a non-empty list or targets_path must point to one.")
    return [ContractTarget.from_json(_target_payload(item)) for item in records]


def run_result_payload(result: Any) -> dict[str, Any]:
    return {
        "run_dir": str(result.run_dir),
        "run_id": result.run_id,
        "status": result.status,
        "executed_count": result.executed_count,
        "skipped_count": result.skipped_count,
        "failed_count": result.failed_count,
        "stop_reason": result.stop_reason,
    }


def _target_payload(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise ValueError("Each target must be an object.")
    return item
