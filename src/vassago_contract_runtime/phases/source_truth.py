"""Phase 05 source-truth skeleton adapter."""

from __future__ import annotations

from typing import Any

from vassago_contract_runtime.design_runtime.models import short_hash
from vassago_contract_runtime.design_runtime.runner import PhaseContext, PhaseResult
from vassago_contract_runtime.sc01_nomad import evaluate_nomad_bridge_root_proof
from vassago_contract_runtime.sc01_source import (
    evaluate_access_control_initializer,
    evaluate_known_non_sc01_pattern,
    evaluate_proxy_storage_collision_reinitializer,
    evaluate_public_normal_behavior,
    evaluate_uninitialized_uups_initializer,
    evaluate_wormhole_uninitialized_implementation,
)


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
        source_manifest = _read_json(context, "01_dossier", "source-manifest.json")
        reviews = [
            _review_queue_item(item, surface, guard_map, state_map, source_manifest)
            for item in queue.get("queue", [])
        ]
        verified_count = sum(1 for item in reviews if item.get("source_truth_verified") is True)
        rejected_count = sum(1 for item in reviews if item.get("status") == "source_truth_rejected")
        status = _source_truth_status(reviews, verified_count, rejected_count)
        return PhaseResult.completed(
            json_artifacts={
                "sc01-source-truth.json": {
                    "status": status,
                    "target_id": context.target.target_id,
                    "review_count": len(reviews),
                    "source_truth_verified_count": verified_count,
                    "source_truth_rejected_count": rejected_count,
                    "reviews": reviews,
                    "evidence_status": "static_only",
                    "blockers": _source_truth_blockers(status),
                    "warning": _source_truth_warning(status),
                }
            }
        )


def _read_json(context: PhaseContext, phase_id: str, name: str) -> dict:
    uri = context.artifact_store.uri(context.target.target_id, phase_id, name)
    payload = context.artifact_store.read_artifact(uri)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON artifact for {phase_id}/{name}")
    return payload


def _source_truth_status(reviews: list[dict[str, Any]], verified_count: int, rejected_count: int) -> str:
    if verified_count:
        return "source_truth_verified"
    if reviews and rejected_count == len(reviews):
        return "source_truth_rejected"
    return "blocked"


def _source_truth_blockers(status: str) -> list[str]:
    if status in {"source_truth_verified", "source_truth_rejected"}:
        return []
    return ["manual_or_slither_source_truth_required", "onchain_state_required"]


def _source_truth_warning(status: str) -> str:
    if status == "source_truth_verified":
        return "Source-backed SC01 initializer truth verified; live impact still depends on state/proxy sidecars."
    if status == "source_truth_rejected":
        return "Source-backed negative policy rejected all SC01 candidates before Foundry."
    return "Skeleton source truth. No candidate is verified or runtime-ready in this phase."


def _review_queue_item(
    item: dict[str, Any],
    surface: dict,
    guard_map: dict,
    state_map: dict,
    source_manifest: dict,
) -> dict[str, Any]:
    functions = list(item.get("matched_functions") or [])
    related_surface = _functions(functions, surface)
    related_guards = _guards(functions, guard_map)
    related_writes = _writes(functions, state_map)
    has_source = any(function.get("source_status") == "found" for function in related_surface)
    known_non_sc01 = evaluate_known_non_sc01_pattern(source_manifest, str(item.get("thesis_id") or ""), functions)
    if known_non_sc01.get("rejected") is True:
        return _rejected_review(
            item,
            functions,
            related_surface,
            related_guards,
            related_writes,
            known_non_sc01,
            "terminal_no_foundry_known_non_sc01_pattern",
        )
    proxy_collision = evaluate_proxy_storage_collision_reinitializer(source_manifest)
    if item.get("thesis_id") == "proxy_storage_collision_reinitializer" and proxy_collision.get("proxy_side_verified") is True:
        if proxy_collision.get("verified") is True:
            return _verified_initializer_review(
                item,
                functions,
                related_surface,
                related_guards,
                related_writes,
                proxy_collision,
                runtime_runner="proxy_storage_collision_runtime",
                evidence_kind="proxy_storage_collision_reinitializer",
            )
        return _partial_proxy_collision_review(
            item,
            functions,
            related_surface,
            related_guards,
            related_writes,
            proxy_collision,
        )
    wormhole = evaluate_wormhole_uninitialized_implementation(source_manifest)
    if item.get("thesis_id") == "uninitialized_implementation_proxy" and wormhole.get("verified") is True:
        return _verified_runtime_specific_review(
            item,
            functions,
            related_surface,
            related_guards,
            related_writes,
            wormhole,
            runtime_runner="wormhole_implementation_runtime",
            evidence_kind="wormhole_uninitialized_implementation",
        )
    nomad = evaluate_nomad_bridge_root_proof(source_manifest)
    if item.get("thesis_id") == "bridge_root_proof_validation" and nomad.get("verified") is True:
        return _verified_runtime_specific_review(
            item,
            functions,
            related_surface,
            related_guards,
            related_writes,
            nomad,
            runtime_runner="nomad_bridge_root_proof_runtime",
            evidence_kind="nomad_root_proof_message_auth_bypass",
        )
    evaluation = evaluate_uninitialized_uups_initializer(source_manifest)
    if _is_verified_uninitialized_uups_initializer(item, related_surface, related_writes, evaluation):
        return _verified_initializer_review(
            item,
            functions,
            related_surface,
            related_guards,
            related_writes,
            evaluation,
            runtime_runner="initializer_runtime",
            evidence_kind="uups_uninitialized_initializer",
        )
    access_control = evaluate_access_control_initializer(source_manifest)
    if _is_verified_access_control_initializer(item, related_surface, access_control):
        return _verified_initializer_review(
            item,
            functions,
            related_surface,
            related_guards,
            related_writes,
            access_control,
            runtime_runner="access_control_initializer_runtime",
            evidence_kind="access_control_uninitialized_initializer",
        )
    normal_behavior = evaluate_public_normal_behavior(source_manifest, functions)
    if normal_behavior.get("rejected") is True:
        return _rejected_review(
            item,
            functions,
            related_surface,
            related_guards,
            related_writes,
            normal_behavior,
            "terminal_no_foundry_public_normal_behavior",
        )
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


def _verified_initializer_review(
    item: dict[str, Any],
    functions: list[str],
    related_surface: list[dict[str, Any]],
    related_guards: list[dict[str, Any]],
    related_writes: list[dict[str, Any]],
    evaluation: dict[str, Any],
    *,
    runtime_runner: str,
    evidence_kind: str,
) -> dict[str, Any]:
    return {
        "source_truth_id": f"ST-{short_hash(str(item.get('queue_id')))}",
        "queue_id": item.get("queue_id"),
        "candidate_id": item.get("candidate_id"),
        "thesis_id": item.get("thesis_id"),
        "status": "source_truth_verified",
        "source_truth_verified": True,
        "evidence_kind": evidence_kind,
        "matched_functions": functions,
        "related_guard_classes": [guard.get("guard_class") for guard in related_guards],
        "related_state_variables": [write.get("variable") for write in related_writes],
        "missing_proof_pieces": [],
        "runtime_runner": runtime_runner,
        "actor_model": "any_external_caller",
        "codable_args": list(evaluation.get("codable_args") or []),
        "harness_setup": list(evaluation.get("harness_setup") or []),
        "measurable_reader": evaluation.get("measurable_reader") or evaluation.get("admin_reader"),
        "measurable_delta": evaluation.get("measurable_delta"),
        "explicit_predicate": evaluation.get("explicit_predicate"),
        "initializer_call_plan": evaluation.get("initializer_call_plan"),
        "initializer_privileged_writes": list(evaluation.get("initializer_privileged_writes") or []),
        "implementation_address": evaluation.get("implementation_address"),
        "implementation_contract_name": evaluation.get("implementation_contract_name"),
        "next_required_adapter": "compile_only_then_local_foundry",
        "evidence_refs": _refs(related_surface, related_guards, related_writes)
        + list(evaluation.get("evidence_refs") or []),
    }


def _partial_proxy_collision_review(
    item: dict[str, Any],
    functions: list[str],
    related_surface: list[dict[str, Any]],
    related_guards: list[dict[str, Any]],
    related_writes: list[dict[str, Any]],
    evaluation: dict[str, Any],
) -> dict[str, Any]:
    return {
        "source_truth_id": f"ST-{short_hash(str(item.get('queue_id')))}",
        "queue_id": item.get("queue_id"),
        "candidate_id": item.get("candidate_id"),
        "thesis_id": item.get("thesis_id"),
        "status": "source_truth_blocked_proxy_side_verified",
        "source_truth_verified": False,
        "evidence_kind": "proxy_storage_collision_reinitializer_candidate",
        "matched_functions": functions,
        "related_guard_classes": [guard.get("guard_class") for guard in related_guards],
        "related_state_variables": [write.get("variable") for write in related_writes],
        "implementation_address": evaluation.get("implementation_address"),
        "implementation_source_status": evaluation.get("implementation_source_status"),
        "implementation_contract_name": evaluation.get("implementation_contract_name"),
        "implementation_initializable": evaluation.get("implementation_initializable"),
        "implementation_initializers": list(evaluation.get("implementation_initializers") or []),
        "initializer_privileged_writes": list(evaluation.get("initializer_privileged_writes") or []),
        "proxy_admin_variable": evaluation.get("proxy_admin_variable"),
        "proxy_admin_reader": evaluation.get("proxy_admin_reader"),
        "implementation_reader": evaluation.get("implementation_reader"),
        "missing_proof_pieces": list(evaluation.get("missing_proof_pieces") or []),
        "measurable_delta": evaluation.get("measurable_delta"),
        "explicit_predicate": evaluation.get("explicit_predicate"),
        "next_required_adapter": "implementation_source_layout_and_delegatecall_initializer_mapper",
        "evidence_refs": _refs(related_surface, related_guards, related_writes)
        + list(evaluation.get("evidence_refs") or []),
    }


def _verified_runtime_specific_review(
    item: dict[str, Any],
    functions: list[str],
    related_surface: list[dict[str, Any]],
    related_guards: list[dict[str, Any]],
    related_writes: list[dict[str, Any]],
    evaluation: dict[str, Any],
    *,
    runtime_runner: str,
    evidence_kind: str,
) -> dict[str, Any]:
    missing = list(evaluation.get("missing_proof_pieces") or [])
    complete = not missing
    return {
        "source_truth_id": f"ST-{short_hash(str(item.get('queue_id')))}",
        "queue_id": item.get("queue_id"),
        "candidate_id": item.get("candidate_id"),
        "thesis_id": item.get("thesis_id"),
        "status": "source_truth_verified" if complete else "source_truth_verified_runtime_blocked",
        "source_truth_verified": True,
        "evidence_kind": evidence_kind,
        "matched_functions": functions,
        "related_guard_classes": [guard.get("guard_class") for guard in related_guards],
        "related_state_variables": [write.get("variable") for write in related_writes],
        "missing_proof_pieces": missing,
        "runtime_runner": runtime_runner,
        "actor_model": evaluation.get("actor_model") or "needs_runtime_actor_model",
        "codable_args": list(evaluation.get("codable_args") or []),
        "measurable_reader": evaluation.get("measurable_reader"),
        "measurable_delta": evaluation.get("measurable_delta"),
        "explicit_predicate": evaluation.get("explicit_predicate"),
        "implementation_address": evaluation.get("implementation_address"),
        "fork_block_number": evaluation.get("fork_block_number"),
        "runtime_strategy": evaluation.get("runtime_strategy"),
        "runtime_components": list(evaluation.get("runtime_components") or []),
        "next_required_adapter": "compile_only_then_local_foundry" if complete else runtime_runner,
        "evidence_refs": _refs(related_surface, related_guards, related_writes)
        + list(evaluation.get("evidence_refs") or []),
    }


def _rejected_review(
    item: dict[str, Any],
    functions: list[str],
    related_surface: list[dict[str, Any]],
    related_guards: list[dict[str, Any]],
    related_writes: list[dict[str, Any]],
    classification: dict[str, Any],
    next_required_adapter: str,
) -> dict[str, Any]:
    return {
        "source_truth_id": f"ST-{short_hash(str(item.get('queue_id')))}",
        "queue_id": item.get("queue_id"),
        "candidate_id": item.get("candidate_id"),
        "thesis_id": item.get("thesis_id"),
        "status": "source_truth_rejected",
        "source_truth_verified": False,
        "matched_functions": functions,
        "classification": classification.get("classification"),
        "reason": classification.get("reason"),
        "related_guard_classes": [guard.get("guard_class") for guard in related_guards],
        "related_state_variables": [write.get("variable") for write in related_writes],
        "missing_proof_pieces": [
            "source_truth_guard_gap",
            "actor_model",
            "measurable_reader",
            "measurable_delta",
            "explicit_predicate",
        ],
        "next_required_adapter": next_required_adapter,
        "evidence_refs": _refs(related_surface, related_guards, related_writes)
        + list(classification.get("evidence_refs") or []),
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
        if any(_matches_function_name(str(writer.get("function") or ""), names) for writer in writers):
            hits.append(variable)
    return hits


def _refs(functions: list[dict[str, Any]], guards: list[dict[str, Any]], writes: list[dict[str, Any]]) -> list[str]:
    refs = []
    refs.extend(f"access-surface:{item.get('signature')}" for item in functions)
    refs.extend(f"guard-map:{item.get('function')}" for item in guards)
    refs.extend(f"state-write-map:{item.get('variable')}" for item in writes)
    return sorted(set(refs))


def _matches_function_name(value: str, names: list[str]) -> bool:
    return value in names or any(str(name).split("(")[0] == value.split("(")[0] for name in names)


def _is_verified_uninitialized_uups_initializer(
    item: dict[str, Any],
    functions: list[dict[str, Any]],
    writes: list[dict[str, Any]],
    evaluation: dict[str, Any],
) -> bool:
    if item.get("thesis_id") != "uninitialized_implementation_proxy":
        return False
    if evaluation.get("verified") is not True:
        return False
    names = {str(function.get("name") or "") for function in functions}
    if "initialize" not in names:
        return False
    variables = {str(item.get("variable") or "") for item in writes}
    return str(evaluation.get("admin_variable") or "") in variables


def _is_verified_access_control_initializer(
    item: dict[str, Any],
    functions: list[dict[str, Any]],
    evaluation: dict[str, Any],
) -> bool:
    if item.get("thesis_id") != "uninitialized_implementation_proxy":
        return False
    if evaluation.get("verified") is not True:
        return False
    names = {str(function.get("name") or "") for function in functions}
    return "initialize" in names
