"""Built-in phase adapters for bootstrap and dry-run flows."""

from __future__ import annotations

from .runner import PhaseAdapter, PhaseContext, PhaseResult


class DryRunPhaseAdapter:
    """Adapter that writes expected phase outputs with dry-run metadata."""

    def run(self, context: PhaseContext) -> PhaseResult:
        artifacts = {}
        if not context.phase.outputs:
            artifacts[f"{context.phase.phase_id}-dry-run.json"] = _payload(context)
        for output in context.phase.outputs:
            if output.name.endswith(".json"):
                artifacts[output.name] = _payload(context)
        text_artifacts = {
            output.name: f"# Dry Run\n\nPhase `{context.phase.phase_id}` did not execute real analysis.\n"
            for output in context.phase.outputs
            if not output.name.endswith(".json")
        }
        return PhaseResult(status=PhaseResult.completed().status, json_artifacts=artifacts, text_artifacts=text_artifacts)


def dry_run_adapters(phase_ids: list[str]) -> dict[str, PhaseAdapter]:
    return {phase_id: DryRunPhaseAdapter() for phase_id in phase_ids}


def _payload(context: PhaseContext) -> dict[str, object]:
    return {
        "status": "dry_run",
        "design_id": context.design.design_id,
        "target_id": context.target.target_id,
        "chain": context.target.chain,
        "address": context.target.address,
        "phase_id": context.phase.phase_id,
        "evidence_status": "static_only",
        "note": "Bootstrap dry-run artifact. No provider, RPC, Slither, Foundry or evidence promotion was used.",
    }
