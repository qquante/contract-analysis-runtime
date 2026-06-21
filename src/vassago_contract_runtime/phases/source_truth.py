"""Phase 05 source-truth skeleton adapter."""

from __future__ import annotations

from typing import Any

from vassago_contract_runtime.design_runtime.models import short_hash
from vassago_contract_runtime.design_runtime.runner import PhaseContext, PhaseResult


class SourceTruthAdapter:
    """Create source-truth review records without promoting evidence.

    The skeleton verifies that static sidecars exist and records which proof
    pieces are still missing. It does not claim a vulnerability.
    """

    def run(self, context: PhaseContext) -> PhaseResult:
        queue = _read_json(context, "04_thesis_acquisition", "sc01-thesis-queue.json")
        surface = _read_json(context, "02_semantic_surface", "access-surface.json")
        guard_map = _read_json(context, "02_semantic_surface", "guard-map.json")
        state_map = _read_json(context, "02_semantic_surface", "state-write-map.json")
        reviews = [_review_queue_item(item, surface, guard_map, state_map) for item in queue.get("queue", [])]
        return PhaseResult.completed(
            json_artifacts={
                "sc01-source-truth.json": {
                    "status": "blocked",
                    "target_id": context.target.target_id,
                    "review_count": len(reviews),
                    "source_truth_verified_count": 0,
                    "reviews": reviews,
                    "evidence_status": "static_only",
                    "blockers": ["manual_or_slither_source_truth_required", "onchain_state_required"],
                    "warning": "Skeleton source truth. No candidate is verified or runtime-ready in this phase.",
                }
            }
        )


def _read_json(context: PhaseContext, phase_id: str, name: str) -> dict:
    uri = context.artifact_store.uri(context.target.target_id, phase_id, name)
    payload = context.artifact_store.read_artifact(uri)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON artifact for {phase_id}/{name}")
    return payload


def _review_queue_item(item: dict[str, Any], surface: dict, guard_map: dict, state_map: dict) -> dict[str, Any]:
    functions = list(item.get("matched_functions") or [])
    related_surface = _functions(functions, surface)
    related_guards = _guards(functions, guard_map)
    related_writes = _writes(functions, state_map)
    has_source = any(function.get("source_status") == "found" for function in related_surface)
    return {
        "source_truth_id": f"ST-{short_hash(str(item.get('queue_id')))}",
        "queue_id": item.get("queue_id"),
        "candidate_id": item.get("candidate_id"),
        "thesis_id": item.get("thesis_id"),
        "status": "source_context_present" if has_source else "source_context_missing",
        "source_truth_verified": False,
        "matched_functions": functions,
        "related_guard_classes": [guard.get("guard_class") for guard in related_guards],
        "related_state_variables": [write.get("variable") for write in related_writes],
        "missing_proof_pieces": [
            "source_truth_guard_gap",
            "actor_model",
            "codable_args",
            "measurable_reader",
            "measurable_delta",
            "explicit_predicate",
        ],
        "next_required_adapter": "slither_or_manual_source_truth",
        "evidence_refs": _refs(related_surface, related_guards, related_writes),
    }


def _functions(names: list[str], surface: dict) -> list[dict[str, Any]]:
    return [
        item
        for item in surface.get("functions", [])
        if item.get("signature") in names or any(str(name).split("(")[0] == item.get("name") for name in names)
    ]


def _guards(names: list[str], guard_map: dict) -> list[dict[str, Any]]:
    return [
        item
        for item in guard_map.get("guards", [])
        if item.get("function") in names or any(str(name).split("(")[0] in str(item.get("function")) for name in names)
    ]


def _writes(names: list[str], state_map: dict) -> list[dict[str, Any]]:
    hits = []
    for variable in state_map.get("state_variables", []):
        writers = variable.get("writers", [])
        if any(writer.get("function") in names for writer in writers):
            hits.append(variable)
    return hits


def _refs(functions: list[dict[str, Any]], guards: list[dict[str, Any]], writes: list[dict[str, Any]]) -> list[str]:
    refs = []
    refs.extend(f"access-surface:{item.get('signature')}" for item in functions)
    refs.extend(f"guard-map:{item.get('function')}" for item in guards)
    refs.extend(f"state-write-map:{item.get('variable')}" for item in writes)
    return sorted(set(refs))
