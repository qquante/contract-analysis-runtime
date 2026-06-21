"""Run and phase manifest helpers."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import tempfile
from typing import Any

from .models import ContractTarget, DesignSpec, PhaseSpec, PhaseStatus, RunOptions, short_hash


RUN_MANIFEST = "run-manifest.json"
TARGET_MANIFEST = "target-manifest.json"
PHASE_MANIFEST = "phase-manifest.json"


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def make_run_id(design: DesignSpec, targets: list[ContractTarget], created_at: str | None = None) -> str:
    seed = "|".join([design.design_id, design.version, *(target.target_id for target in targets), created_at or utc_now()])
    return f"RUN-{short_hash(seed)}"


def create_run_manifest(
    run_dir: str | Path,
    design: DesignSpec,
    targets: list[ContractTarget],
    options: RunOptions | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Create a fresh run directory and write run/target manifests."""

    options = options or RunOptions()
    root = Path(run_dir)
    root.mkdir(parents=True, exist_ok=True)
    created_at = utc_now()
    run_id = run_id or make_run_id(design, targets, created_at=created_at)
    manifest = {
        "kind": "vassago-contract-runtime-run",
        "run_id": run_id,
        "design": design.to_json(),
        "created_at": created_at,
        "updated_at": created_at,
        "options": options.to_json(),
        "summary": {
            "target_count": len(targets),
            "phase_count": len(design.phases),
            "status": "created",
        },
        "targets": [_target_manifest_payload(target, design.phases) for target in targets],
    }
    atomic_write_json(root / RUN_MANIFEST, manifest)
    for target in targets:
        target_dir = target_root(root, target.target_id)
        target_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(target_dir / TARGET_MANIFEST, _target_manifest_payload(target, design.phases))
        for phase in design.phases:
            phase_dir = phase_root(root, target.target_id, phase.phase_id)
            phase_dir.mkdir(parents=True, exist_ok=True)
            atomic_write_json(
                phase_dir / PHASE_MANIFEST,
                _phase_manifest_payload(phase, PhaseStatus.PENDING, updated_at=created_at),
            )
    return manifest


def load_run_manifest(run_dir: str | Path) -> dict[str, Any]:
    return read_json(Path(run_dir) / RUN_MANIFEST)


def update_run_summary(run_dir: str | Path, **updates: Any) -> dict[str, Any]:
    root = Path(run_dir)
    manifest = load_run_manifest(root)
    manifest.setdefault("summary", {}).update(updates)
    manifest["updated_at"] = utc_now()
    atomic_write_json(root / RUN_MANIFEST, manifest)
    return manifest


def update_phase_status(
    run_dir: str | Path,
    target_id: str,
    phase: PhaseSpec,
    status: PhaseStatus,
    *,
    artifacts: list[dict[str, Any]] | None = None,
    error: dict[str, Any] | None = None,
    stop_reason: str | None = None,
) -> dict[str, Any]:
    root = Path(run_dir)
    now = utc_now()
    phase_payload = _phase_manifest_payload(
        phase,
        status,
        artifacts=artifacts or [],
        error=error,
        stop_reason=stop_reason,
        updated_at=now,
    )
    atomic_write_json(phase_root(root, target_id, phase.phase_id) / PHASE_MANIFEST, phase_payload)

    target_manifest_path = target_root(root, target_id) / TARGET_MANIFEST
    target_manifest = read_json(target_manifest_path)
    for item in target_manifest.get("phases", []):
        if item.get("phase_id") == phase.phase_id:
            item.update(
                {
                    "status": status.value,
                    "updated_at": now,
                    "artifact_count": len(artifacts or []),
                    "stop_reason": stop_reason,
                }
            )
            break
    atomic_write_json(target_manifest_path, target_manifest)

    run_manifest = load_run_manifest(root)
    for target in run_manifest.get("targets", []):
        if target.get("target_id") != target_id:
            continue
        for item in target.get("phases", []):
            if item.get("phase_id") == phase.phase_id:
                item.update(
                    {
                        "status": status.value,
                        "updated_at": now,
                        "artifact_count": len(artifacts or []),
                        "stop_reason": stop_reason,
                    }
                )
                break
    run_manifest["updated_at"] = now
    atomic_write_json(root / RUN_MANIFEST, run_manifest)
    return phase_payload


def phase_status(run_dir: str | Path, target_id: str, phase_id: str) -> PhaseStatus:
    path = phase_root(Path(run_dir), target_id, phase_id) / PHASE_MANIFEST
    if not path.is_file():
        return PhaseStatus.PENDING
    value = read_json(path).get("status", PhaseStatus.PENDING.value)
    return PhaseStatus(value)


def target_root(run_dir: Path, target_id: str) -> Path:
    return run_dir / "targets" / target_id


def phase_root(run_dir: Path, target_id: str, phase_id: str) -> Path:
    return target_root(run_dir, target_id) / "phases" / phase_id


def read_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def atomic_write_json(path: str | Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(text)
        tmp_path = Path(handle.name)
    tmp_path.replace(path)


def _target_manifest_payload(target: ContractTarget, phases: tuple[PhaseSpec, ...]) -> dict[str, Any]:
    return {
        "kind": "vassago-contract-runtime-target",
        **target.to_json(),
        "phases": [
            {
                "phase_id": phase.phase_id,
                "name": phase.name,
                "required": phase.required,
                "status": PhaseStatus.PENDING.value,
                "artifact_count": 0,
                "updated_at": None,
                "stop_reason": None,
            }
            for phase in phases
        ],
    }


def _phase_manifest_payload(
    phase: PhaseSpec,
    status: PhaseStatus,
    *,
    artifacts: list[dict[str, Any]] | None = None,
    error: dict[str, Any] | None = None,
    stop_reason: str | None = None,
    updated_at: str | None = None,
) -> dict[str, Any]:
    return {
        "kind": "vassago-contract-runtime-phase",
        "phase_id": phase.phase_id,
        "name": phase.name,
        "required": phase.required,
        "status": status.value,
        "updated_at": updated_at or utc_now(),
        "stop_reason": stop_reason,
        "expected_outputs": [item.to_json() for item in phase.outputs],
        "artifacts": artifacts or [],
        "error": error,
    }
