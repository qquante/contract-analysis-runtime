"""Phase runner with resumable manifests."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from vassago_contract_runtime.artifacts.store import ArtifactStore

from .manifest import (
    create_run_manifest,
    load_run_manifest,
    phase_status,
    update_phase_status,
    update_run_summary,
)
from .models import ContractTarget, DesignSpec, PhaseSpec, PhaseStatus, RunOptions


class PhaseAdapter(Protocol):
    def run(self, context: "PhaseContext") -> "PhaseResult":
        """Run one phase for one target."""


@dataclass(frozen=True)
class PhaseContext:
    run_dir: Path
    run_id: str
    design: DesignSpec
    target: ContractTarget
    phase: PhaseSpec
    options: RunOptions
    artifact_store: ArtifactStore


@dataclass
class PhaseResult:
    status: PhaseStatus = PhaseStatus.COMPLETED
    json_artifacts: dict[str, dict[str, Any]] = field(default_factory=dict)
    text_artifacts: dict[str, str] = field(default_factory=dict)
    error: dict[str, Any] | None = None
    stop_reason: str | None = None

    @classmethod
    def completed(cls, *, json_artifacts: dict[str, dict[str, Any]] | None = None) -> "PhaseResult":
        return cls(status=PhaseStatus.COMPLETED, json_artifacts=json_artifacts or {})

    @classmethod
    def failed(cls, code: str, message: str, *, stop_reason: str | None = None) -> "PhaseResult":
        return cls(status=PhaseStatus.FAILED, error={"code": code, "message": message}, stop_reason=stop_reason or code)


@dataclass(frozen=True)
class RunResult:
    run_dir: Path
    run_id: str
    status: str
    executed_count: int
    skipped_count: int
    failed_count: int
    stop_reason: str | None = None


def run_design(
    design: DesignSpec,
    targets: list[ContractTarget],
    output_dir: str | Path,
    adapters: dict[str, PhaseAdapter],
    options: RunOptions | None = None,
) -> RunResult:
    options = options or RunOptions()
    run_dir = Path(output_dir)
    if (run_dir / "run-manifest.json").is_file() and options.resume:
        return resume_design(run_dir, adapters, options=options)
    manifest = create_run_manifest(run_dir, design, targets, options)
    return _execute(run_dir, design, targets, adapters, manifest["run_id"], options)


def resume_design(
    run_dir: str | Path,
    adapters: dict[str, PhaseAdapter],
    options: RunOptions | None = None,
) -> RunResult:
    options = options or RunOptions()
    run_dir = Path(run_dir)
    manifest = load_run_manifest(run_dir)
    design = DesignSpec.from_json(manifest["design"])
    targets = [ContractTarget.from_json(item) for item in manifest.get("targets", [])]
    return _execute(run_dir, design, targets, adapters, manifest["run_id"], options)


def run_phase(context: PhaseContext, adapter: PhaseAdapter) -> list[dict[str, Any]]:
    update_phase_status(context.run_dir, context.target.target_id, context.phase, PhaseStatus.RUNNING)
    result = adapter.run(context)
    artifact_refs: list[dict[str, Any]] = []
    for name, payload in result.json_artifacts.items():
        artifact_refs.append(
            context.artifact_store.write_json_artifact(context.target.target_id, context.phase.phase_id, name, payload)
        )
    for name, text in result.text_artifacts.items():
        artifact_refs.append(
            context.artifact_store.write_text_artifact(context.target.target_id, context.phase.phase_id, name, text)
        )
    update_phase_status(
        context.run_dir,
        context.target.target_id,
        context.phase,
        result.status,
        artifacts=artifact_refs,
        error=result.error,
        stop_reason=result.stop_reason,
    )
    return artifact_refs


def _execute(
    run_dir: Path,
    design: DesignSpec,
    targets: list[ContractTarget],
    adapters: dict[str, PhaseAdapter],
    run_id: str,
    options: RunOptions,
) -> RunResult:
    artifact_store = ArtifactStore(run_dir, run_id)
    executed_count = 0
    skipped_count = 0
    failed_count = 0
    stop_reason: str | None = None
    for target in targets:
        target_stopped = False
        for phase in design.phases:
            current = phase_status(run_dir, target.target_id, phase.phase_id)
            if current == PhaseStatus.COMPLETED and options.resume:
                skipped_count += 1
                continue
            if target_stopped:
                update_phase_status(
                    run_dir,
                    target.target_id,
                    phase,
                    PhaseStatus.SKIPPED,
                    stop_reason="previous_required_phase_failed",
                )
                skipped_count += 1
                continue
            adapter = adapters.get(phase.phase_id)
            if adapter is None:
                failure = PhaseResult.failed("missing_phase_adapter", f"No adapter registered for {phase.phase_id}")
                update_phase_status(
                    run_dir,
                    target.target_id,
                    phase,
                    failure.status,
                    error=failure.error,
                    stop_reason=failure.stop_reason,
                )
                failed_count += 1
                executed_count += 1
                if phase.required:
                    target_stopped = True
                    stop_reason = failure.stop_reason
                continue
            context = PhaseContext(
                run_dir=run_dir,
                run_id=run_id,
                design=design,
                target=target,
                phase=phase,
                options=options,
                artifact_store=artifact_store,
            )
            try:
                run_phase(context, adapter)
                final_status = phase_status(run_dir, target.target_id, phase.phase_id)
            except Exception as exc:  # pragma: no cover - defensive path tested through fake adapter failures.
                final_status = PhaseStatus.FAILED
                update_phase_status(
                    run_dir,
                    target.target_id,
                    phase,
                    PhaseStatus.FAILED,
                    error={"code": "phase_exception", "message": str(exc)},
                    stop_reason="phase_exception",
                )
            executed_count += 1
            if final_status == PhaseStatus.FAILED:
                failed_count += 1
                if phase.required or not options.continue_optional_failures:
                    target_stopped = True
                    stop_reason = "required_phase_failed" if phase.required else "optional_phase_failed"
    status = "completed" if failed_count == 0 else "completed_with_failures"
    if stop_reason and failed_count:
        status = "stopped"
    update_run_summary(
        run_dir,
        status=status,
        executed_count=executed_count,
        skipped_count=skipped_count,
        failed_count=failed_count,
        stop_reason=stop_reason,
    )
    return RunResult(
        run_dir=run_dir,
        run_id=run_id,
        status=status,
        executed_count=executed_count,
        skipped_count=skipped_count,
        failed_count=failed_count,
        stop_reason=stop_reason,
    )
