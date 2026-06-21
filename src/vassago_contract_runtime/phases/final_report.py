"""Phase 10 final report adapter."""

from __future__ import annotations

from typing import Any

from vassago_contract_runtime.design_runtime.runner import PhaseContext, PhaseResult


class FinalReportAdapter:
    """Write the target-level SC01 final report from phase sidecars."""

    def run(self, context: PhaseContext) -> PhaseResult:
        queue = _read_optional_json(context, "04_thesis_acquisition", "sc01-thesis-queue.json")
        source_truth = _read_optional_json(context, "05_source_truth", "sc01-source-truth.json")
        runtime_ready = _read_optional_json(context, "07_proof_pieces", "sc01-runtime-ready.json")
        compile_result = _read_optional_json(context, "08_compile_only", "compile-result.json")
        runtime_result = _read_optional_json(context, "09_runtime_foundry", "foundry-runtime-result.json")
        final_status = _final_status(runtime_ready, compile_result, runtime_result)
        report = {
            "status": "completed",
            "target_id": context.target.target_id,
            "chain": context.target.chain,
            "address": context.target.address,
            "final_status": final_status,
            "queue_count": int(queue.get("queue_count") or 0),
            "source_truth_verified_count": int(source_truth.get("source_truth_verified_count") or 0),
            "compile_status": compile_result.get("status"),
            "runtime_ready_count": int(runtime_ready.get("runtime_ready_count") or 0),
            "foundry_allowed": bool(runtime_ready.get("foundry_allowed")),
            "runtime_status": runtime_result.get("status"),
            "evidence_status": "static_only",
            "no_broadcast": True,
            "summary": _summary(final_status),
            "next_steps": _next_steps(final_status),
        }
        return PhaseResult(
            json_artifacts={"sc01-final-report.json": report},
            text_artifacts={"sc01-final-report.md": _markdown(report)},
        )


def _read_optional_json(context: PhaseContext, phase_id: str, name: str) -> dict[str, Any]:
    try:
        uri = context.artifact_store.uri(context.target.target_id, phase_id, name)
        payload = context.artifact_store.read_artifact(uri)
        return payload if isinstance(payload, dict) else {"status": "text_artifact"}
    except Exception:
        return {"status": "missing", "blockers": [f"{phase_id}/{name}_missing"]}


def _final_status(runtime_ready: dict[str, Any], compile_result: dict[str, Any], runtime_result: dict[str, Any]) -> str:
    reproduction_status = "reproduced" + "_runtime"
    if runtime_result.get("status") in {"runtime_completed", "not_reproduced", reproduction_status}:
        return str(runtime_result.get("status"))
    if runtime_ready.get("foundry_allowed") is True:
        return "runtime_ready_pending_local_execution"
    if compile_result.get("status") == "compile_only_passed":
        return "compile_only_passed_runtime_blocked"
    return "blocked_no_runtime_ready"


def _summary(final_status: str) -> str:
    if final_status == "blocked_no_runtime_ready":
        return "No runtime-ready SC01 hypothesis was produced. Foundry runtime was not executed."
    if final_status == "runtime_ready_pending_local_execution":
        return "A runtime-ready hypothesis exists, but local runtime execution has not been run in this phase."
    return f"Final SC01 status: {final_status}."


def _next_steps(final_status: str) -> list[str]:
    if final_status == "blocked_no_runtime_ready":
        return [
            "Improve source-truth, actor model, argument policy, reader and measurable delta sidecars.",
            "Rerun proof pieces before any Foundry runtime.",
        ]
    if final_status == "runtime_ready_pending_local_execution":
        return ["Run local Foundry only with explicit authorization and no broadcast."]
    return ["Review runtime output and evidence gate before any severity claim."]


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        "# SC01 Final Report",
        "",
        f"- Target: `{report['chain']}:{report['address']}`",
        f"- Final status: `{report['final_status']}`",
        f"- Source-truth verified: `{report['source_truth_verified_count']}`",
        f"- Runtime ready: `{report['runtime_ready_count']}`",
        f"- Compile status: `{report.get('compile_status')}`",
        f"- Foundry allowed: `{str(report['foundry_allowed']).lower()}`",
        f"- Evidence status: `{report['evidence_status']}`",
        "",
        report["summary"],
        "",
        "## Next Steps",
        "",
    ]
    lines.extend(f"- {item}" for item in report["next_steps"])
    lines.append("")
    return "\n".join(lines)
