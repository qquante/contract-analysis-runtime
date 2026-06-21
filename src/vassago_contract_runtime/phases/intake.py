"""Phase 00 intake adapter."""

from __future__ import annotations

from vassago_contract_runtime.design_runtime.runner import PhaseContext, PhaseResult


class IntakeAdapter:
    """Write normalized target and scope policy artifacts."""

    def run(self, context: PhaseContext) -> PhaseResult:
        target_manifest = {
            "status": "completed",
            "phase_id": context.phase.phase_id,
            "target": context.target.to_json(),
            "target_model": context.design.target_model,
            "evidence_status": "static_only",
            "normalization": {
                "chain_lowercase": True,
                "address_lowercase": True,
                "target_id_stable": True,
            },
        }
        scope_policy = {
            "status": "completed",
            "phase_id": context.phase.phase_id,
            "target_id": context.target.target_id,
            "no_broadcast": True,
            "key_material_allowed": False,
            "local_runtime_only": True,
            "allowed_network_actions": ["read_only"],
            "evidence_policy": context.design.evidence_policy,
        }
        return PhaseResult.completed(
            json_artifacts={
                "target-manifest.json": target_manifest,
                "scope-policy.json": scope_policy,
            }
        )
