"""Phase 09 local Foundry runtime adapter."""

from __future__ import annotations

from vassago_contract_runtime.design_runtime.runner import PhaseContext, PhaseResult
from vassago_contract_runtime.foundry import FoundryAdapter, FoundryHarnessInput, NullFoundryAdapter
from vassago_contract_runtime.phases.compile_only import render_sc01_harness


class RuntimeFoundryAdapter:
    """Run local Foundry tests only after the runtime gate is satisfied."""

    def __init__(self, foundry: FoundryAdapter | None = None, *, runtime_authorized: bool = False) -> None:
        self.foundry = foundry or NullFoundryAdapter()
        self.runtime_authorized = runtime_authorized

    def run(self, context: PhaseContext) -> PhaseResult:
        ready = _read_json(context, "07_proof_pieces", "sc01-runtime-ready.json")
        compile_result = _read_json(context, "08_compile_only", "compile-result.json")
        source_manifest = _read_json(context, "01_dossier", "source-manifest.json")
        source_truth = _read_json(context, "05_source_truth", "sc01-source-truth.json")
        if ready.get("foundry_allowed") is not True:
            return _blocked(context, "blocked_no_runtime_ready", ["foundry_allowed_false"])
        if compile_result.get("status") != "compile_only_passed":
            return _blocked(context, "blocked_compile_only_required", ["compile_only_passed_required"])
        if self.runtime_authorized is not True:
            return _blocked(context, "blocked_runtime_authorization_required", ["runtime_authorized_required"])

        item = FoundryHarnessInput(
            target_id=context.target.target_id,
            harness_name="VassagoSC01Harness",
            source_files=dict(source_manifest.get("source_files") or {}),
            test_files={"VassagoSC01Harness.t.sol": render_sc01_harness(source_manifest)},
            metadata={"runtime_ready": True, "runtime_authorized": True},
        )
        result = self.foundry.run_local_fork(item)
        assertion_status = "passed" if result.status == "runtime_completed" else "failed"
        predicate = _runtime_predicate(source_truth)
        measured_delta = _runtime_delta(source_truth)
        return PhaseResult(
            json_artifacts={
                "foundry-runtime-result.json": {
                    "status": result.status,
                    "target_id": context.target.target_id,
                    "foundry_called": True,
                    "foundry": result.to_json(),
                    "evidence_status": "runtime_local" if result.status == "runtime_completed" else "inconclusive",
                    "no_broadcast": True,
                },
                "assertion-result.json": {
                    "status": assertion_status,
                    "target_id": context.target.target_id,
                    "predicate": predicate,
                    "measured_delta": measured_delta,
                    "evidence_status": "runtime_local" if assertion_status == "passed" else "inconclusive",
                },
            },
            text_artifacts={"evidence.md": _evidence_md(result.status, assertion_status)},
        )


def _read_json(context: PhaseContext, phase_id: str, name: str) -> dict:
    uri = context.artifact_store.uri(context.target.target_id, phase_id, name)
    payload = context.artifact_store.read_artifact(uri)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON artifact for {phase_id}/{name}")
    return payload


def _blocked(context: PhaseContext, status: str, blockers: list[str]) -> PhaseResult:
    result = {
        "status": status,
        "target_id": context.target.target_id,
        "foundry_called": False,
        "evidence_status": "static_only",
        "blockers": blockers,
        "no_broadcast": True,
    }
    return PhaseResult(
        json_artifacts={
            "foundry-runtime-result.json": result,
            "assertion-result.json": {
                "status": "not_run",
                "target_id": context.target.target_id,
                "evidence_status": "static_only",
                "blockers": blockers,
            },
        },
        text_artifacts={"evidence.md": f"# Runtime Not Run\n\nStatus: `{status}`.\n"},
    )


def _verified_review(source_truth: dict) -> dict:
    for review in source_truth.get("reviews") or []:
        if review.get("source_truth_verified") is True:
            return review
    return {}


def _runtime_predicate(source_truth: dict) -> str:
    review = _verified_review(source_truth)
    return str(review.get("explicit_predicate") or "SC01 local runtime predicate passed")


def _runtime_delta(source_truth: dict) -> str:
    review = _verified_review(source_truth)
    return str(review.get("measurable_delta") or "SC01 measurable authorization delta observed locally")


def _evidence_md(runtime_status: str, assertion_status: str) -> str:
    return "\n".join(
        [
            "# Local Runtime Evidence",
            "",
            f"- Runtime status: `{runtime_status}`",
            f"- Assertion status: `{assertion_status}`",
            "- Scope: local Foundry runtime only",
            "- Broadcast: no",
            "",
        ]
    )
