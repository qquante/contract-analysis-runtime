"""Command line interface for the contract runtime."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from .design_runtime.adapters import dry_run_adapters
from .design_runtime.design_loader import DesignLoadError, load_design
from .design_runtime.manifest import load_run_manifest
from .design_runtime.models import ContractTarget, ModelValidationError, RunOptions
from .design_runtime.runner import resume_design, run_design
from .artifacts.store import ArtifactStore
from .contracts import FixtureSourceResolver
from .phases.corpus_motifs import CorpusMotifsAdapter
from .phases.compile_only import CompileOnlyAdapter
from .phases.dossier import DossierAdapter
from .phases.final_report import FinalReportAdapter
from .phases.intake import IntakeAdapter
from .phases.onchain_state import OnChainStateAdapter
from .phases.proof_pieces import ProofPiecesAdapter
from .phases.semantic_surface import SemanticSurfaceAdapter
from .phases.source_truth import SourceTruthAdapter
from .phases.thesis_acquisition import ThesisAcquisitionAdapter
from .quality import run_checks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="vassago-contract-runtime")
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="Validate repository runtime metadata.")
    check.add_argument("--root", default=".", help="Repository root.")

    run = sub.add_parser("run-design", help="Run a design against target contracts.")
    run.add_argument("--design", required=True, help="Design id or path to design.yaml.")
    run.add_argument("--targets", required=True, help="JSON target list.")
    run.add_argument("--output", required=True, help="Run output directory.")
    run.add_argument("--dry-run", action="store_true", help="Write manifests and dry-run artifacts only.")
    run.add_argument("--source-fixture", help="Local JSON source fixture for phase 01 dossier.")
    run.add_argument(
        "--bootstrap-adapters",
        action="store_true",
        help="Run implemented bootstrap adapters and dry-run the rest.",
    )
    run.add_argument("--no-resume", action="store_true", help="Do not resume an existing run directory.")

    resume = sub.add_parser("resume", help="Resume an existing run.")
    resume.add_argument("--run", required=True, help="Run directory.")
    resume.add_argument("--dry-run", action="store_true", help="Use dry-run adapters.")
    resume.add_argument("--source-fixture", help="Local JSON source fixture for phase 01 dossier.")
    resume.add_argument(
        "--bootstrap-adapters",
        action="store_true",
        help="Use implemented bootstrap adapters and dry-run the rest.",
    )

    artifact_read = sub.add_parser("artifact-read", help="Read an artifact by vassago:// URI.")
    artifact_read.add_argument("--run", required=True, help="Run directory.")
    artifact_read.add_argument("--uri", required=True, help="Artifact URI.")

    args = parser.parse_args(argv)
    try:
        if args.command == "check":
            result = run_checks(Path(args.root))
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0 if result["status"] == "passed" else 1
        if args.command == "run-design":
            return _run_design_command(args)
        if args.command == "resume":
            return _resume_command(args)
        if args.command == "artifact-read":
            return _artifact_read_command(args)
    except (DesignLoadError, ModelValidationError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 2


def _run_design_command(args: argparse.Namespace) -> int:
    design_path = _design_path(args.design)
    design = load_design(design_path)
    targets = _load_targets(Path(args.targets))
    if not args.dry_run and not args.bootstrap_adapters:
        raise ValueError("Use --dry-run or --bootstrap-adapters until all real phase adapters exist.")
    adapters = _adapters_for(
        design,
        dry_run=args.dry_run,
        bootstrap=args.bootstrap_adapters,
        source_fixture=args.source_fixture,
        design_dir=design_path.parent,
    )
    result = run_design(
        design,
        targets,
        args.output,
        adapters,
        RunOptions(resume=not args.no_resume, dry_run=args.dry_run),
    )
    print(json.dumps(_result_payload(result), indent=2, sort_keys=True))
    return 0 if result.failed_count == 0 else 1


def _resume_command(args: argparse.Namespace) -> int:
    manifest = load_run_manifest(args.run)
    design = load_design_from_manifest(manifest)
    if not args.dry_run and not args.bootstrap_adapters:
        raise ValueError("Use --dry-run or --bootstrap-adapters until all real phase adapters exist.")
    result = resume_design(
        args.run,
        _adapters_for(
            design,
            dry_run=args.dry_run,
            bootstrap=args.bootstrap_adapters,
            source_fixture=args.source_fixture,
            design_dir=Path("designs") / design.design_id,
        ),
        RunOptions(resume=True, dry_run=args.dry_run),
    )
    print(json.dumps(_result_payload(result), indent=2, sort_keys=True))
    return 0 if result.failed_count == 0 else 1


def _artifact_read_command(args: argparse.Namespace) -> int:
    manifest = load_run_manifest(args.run)
    store = ArtifactStore(args.run, manifest["run_id"])
    payload = store.read_artifact(args.uri)
    if isinstance(payload, str):
        print(payload)
    else:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _design_path(value: str) -> Path:
    path = Path(value)
    if path.is_file():
        return path
    return Path("designs") / value / "design.yaml"


def load_design_from_manifest(manifest: dict[str, Any]) -> Any:
    from .design_runtime.models import DesignSpec

    return DesignSpec.from_json(manifest["design"])


def _adapters_for(
    design: Any,
    *,
    dry_run: bool,
    bootstrap: bool,
    source_fixture: str | None = None,
    design_dir: Path | None = None,
) -> dict[str, Any]:
    adapters = dry_run_adapters([phase.phase_id for phase in design.phases])
    if bootstrap and not dry_run:
        source_resolver = FixtureSourceResolver.from_file(source_fixture) if source_fixture else None
        adapters["00_intake"] = IntakeAdapter()
        adapters["01_dossier"] = DossierAdapter(source_resolver)
        adapters["02_semantic_surface"] = SemanticSurfaceAdapter()
        adapters["03_corpus_motifs"] = CorpusMotifsAdapter.from_design_dir(str(design_dir or Path("designs") / design.design_id))
        adapters["04_thesis_acquisition"] = ThesisAcquisitionAdapter()
        adapters["05_source_truth"] = SourceTruthAdapter()
        adapters["06_onchain_state"] = OnChainStateAdapter()
        adapters["07_proof_pieces"] = ProofPiecesAdapter()
        adapters["08_compile_only"] = CompileOnlyAdapter()
        adapters["10_final_report"] = FinalReportAdapter()
    return adapters


def _load_targets(path: Path) -> list[ContractTarget]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        records = payload.get("targets", [])
    else:
        records = payload
    if not isinstance(records, list) or not records:
        raise ValueError("Targets file must contain a non-empty list or {'targets': [...]}.")
    return [ContractTarget.from_json(_target_payload(item)) for item in records]


def _target_payload(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise ValueError("Each target must be an object.")
    return item


def _result_payload(result: Any) -> dict[str, Any]:
    return {
        "run_dir": str(result.run_dir),
        "run_id": result.run_id,
        "status": result.status,
        "executed_count": result.executed_count,
        "skipped_count": result.skipped_count,
        "failed_count": result.failed_count,
        "stop_reason": result.stop_reason,
    }


if __name__ == "__main__":
    raise SystemExit(main())
