"""Phase 04 thesis acquisition skeleton adapter."""

from __future__ import annotations

from typing import Any

from vassago_contract_runtime.design_runtime.models import short_hash
from vassago_contract_runtime.design_runtime.runner import PhaseContext, PhaseResult


class ThesisAcquisitionAdapter:
    """Rank candidate theses from local static sidecars.

    This phase only decides which thesis should be investigated next. It does
    not verify the thesis and does not enable compile/runtime gates.
    """

    def run(self, context: PhaseContext) -> PhaseResult:
        candidates = _read_json(context, "03_corpus_motifs", "sc01-thesis-candidates.json")
        semantic_map = _read_json(context, "02_semantic_surface", "semantic-map.json")
        guard_map = _read_json(context, "02_semantic_surface", "guard-map.json")
        queue = [_queue_item(item, semantic_map, guard_map) for item in candidates.get("candidates", [])]
        queue.sort(key=lambda item: (item["priority"], item["thesis_id"]))
        report = {
            "status": "completed",
            "candidate_count": len(candidates.get("candidates", [])),
            "queued_count": len(queue),
            "dropped_count": 0,
            "evidence_status": "static_only",
            "warning": "Thesis acquisition is routing only. Source-truth and proof pieces are not run.",
        }
        return PhaseResult.completed(
            json_artifacts={
                "sc01-thesis-queue.json": {
                    "status": "candidate_only" if queue else "empty",
                    "queue": queue,
                    "queue_count": len(queue),
                    "evidence_status": "static_only",
                },
                "sc01-acquisition-report.json": report,
            }
        )


def _read_json(context: PhaseContext, phase_id: str, name: str) -> dict:
    uri = context.artifact_store.uri(context.target.target_id, phase_id, name)
    payload = context.artifact_store.read_artifact(uri)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON artifact for {phase_id}/{name}")
    return payload


def _queue_item(candidate: dict[str, Any], semantic_map: dict[str, Any], guard_map: dict[str, Any]) -> dict[str, Any]:
    thesis_id = str(candidate.get("thesis_id") or "unknown")
    matched_functions = list(candidate.get("matched_functions") or [])
    related_roles = _related_roles(matched_functions, semantic_map)
    related_guards = _related_guards(matched_functions, guard_map)
    blockers = list(candidate.get("blockers") or [])
    blockers.extend(["source_truth_required", "proof_piece_state_required"])
    return {
        "queue_id": f"TQ-{short_hash(candidate.get('candidate_id', thesis_id))}",
        "candidate_id": candidate.get("candidate_id"),
        "target_id": candidate.get("target_id"),
        "chain": candidate.get("chain"),
        "address": candidate.get("address"),
        "thesis_id": thesis_id,
        "priority": _priority(thesis_id, related_roles, related_guards),
        "status": "queued_for_source_truth",
        "matched_motifs": list(candidate.get("matched_motifs") or []),
        "matched_functions": matched_functions,
        "related_semantic_roles": related_roles,
        "related_guard_classes": related_guards,
        "required_next_phase": "05_source_truth",
        "blockers": sorted(set(blockers)),
    }


def _related_roles(functions: list[str], semantic_map: dict[str, Any]) -> list[str]:
    roles = []
    for role in semantic_map.get("roles", []):
        if role.get("function") in functions or any(str(name).split("(")[0] in str(role.get("function")) for name in functions):
            roles.append(str(role.get("semantic_role")))
    return sorted({role for role in roles if role and role != "unknown"})


def _related_guards(functions: list[str], guard_map: dict[str, Any]) -> list[str]:
    guards = []
    for guard in guard_map.get("guards", []):
        if guard.get("function") in functions or any(str(name).split("(")[0] in str(guard.get("function")) for name in functions):
            guards.append(str(guard.get("guard_class")))
    return sorted({guard for guard in guards if guard})


def _priority(thesis_id: str, roles: list[str], guards: list[str]) -> int:
    score = 50
    if thesis_id in {"uups_weak_auth", "uninitialized_implementation_proxy"}:
        score -= 20
    if "implementation_upgrade" in roles or "initializer" in roles:
        score -= 10
    if "none" in guards:
        score -= 5
    return max(score, 1)
