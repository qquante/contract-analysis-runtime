"""Phase 06 on-chain state skeleton adapter."""

from __future__ import annotations

from vassago_contract_runtime.sc01_nomad import NOMAD_EXPLOIT_FORK_BLOCK, build_nomad_root_proof_analysis
from vassago_contract_runtime.design_runtime.runner import PhaseContext, PhaseResult


class OnChainStateAdapter:
    """Prepare on-chain state sidecars without doing RPC by default."""

    def run(self, context: PhaseContext) -> PhaseResult:
        source_manifest = _read_json(context, "01_dossier", "source-manifest.json")
        role_graph = _read_json(context, "02_semantic_surface", "role-graph.json")
        source_truth = _read_json(context, "05_source_truth", "sc01-source-truth.json")
        proxy_context = dict(source_manifest.get("proxy_context") or {})
        nomad_review = _verified_runtime_review(source_truth, {"nomad_bridge_root_proof_runtime"})
        if nomad_review:
            return _nomad_state_result(context, source_manifest, role_graph, source_truth, nomad_review)
        verified_initializer = _verified_initializer_review(source_truth)
        if verified_initializer:
            return PhaseResult.completed(
                json_artifacts={
                    "admin-state.json": {
                        "status": "local_initializer_state_ready",
                        "target_id": context.target.target_id,
                        "admin_candidates": _admin_candidates(role_graph),
                        "source_truth_review_count": source_truth.get("review_count", 0),
                        "reader": verified_initializer.get("measurable_reader"),
                        "initial_value": "deployment default",
                        "post_condition": verified_initializer.get("explicit_predicate"),
                        "evidence_status": "static_only",
                        "note": "Local reproduction state. This does not claim live on-chain impact.",
                        "blockers": [],
                    },
                    "proxy-state.json": {
                        "status": "local_initializer_proxy_context_not_required",
                        "target_id": context.target.target_id,
                        "proxy_context": proxy_context,
                        "has_proxy_hint": False,
                        "note": "Initializer reproduction is local deployment based; live proxy/state impact remains separate.",
                        "evidence_status": "static_only",
                        "blockers": [],
                    },
                    "role-state.json": {
                        "status": "local_initializer_role_state_ready",
                        "target_id": context.target.target_id,
                        "role_graph_nodes": list(role_graph.get("nodes") or []),
                        "role_graph_edges": list(role_graph.get("edges") or []),
                        "actor_model": verified_initializer.get("actor_model") or "any_external_caller",
                        "reader": verified_initializer.get("measurable_reader"),
                        "delta": verified_initializer.get("measurable_delta"),
                        "evidence_status": "static_only",
                        "note": "Role state is asserted only for local Foundry reproduction.",
                        "blockers": [],
                    },
                }
            )
        return PhaseResult.completed(
            json_artifacts={
                "admin-state.json": {
                    "status": "needs_provider",
                    "target_id": context.target.target_id,
                    "admin_candidates": _admin_candidates(role_graph),
                    "source_truth_review_count": source_truth.get("review_count", 0),
                    "evidence_status": "static_only",
                    "blockers": ["rpc_or_explorer_state_reader_required"],
                },
                "proxy-state.json": {
                    "status": "needs_provider",
                    "target_id": context.target.target_id,
                    "proxy_context": proxy_context,
                    "has_proxy_hint": bool(proxy_context.get("implementation") or proxy_context.get("proxy") == "1"),
                    "evidence_status": "static_only",
                    "blockers": ["eip1967_or_explorer_proxy_state_required"],
                },
                "role-state.json": {
                    "status": "needs_provider",
                    "target_id": context.target.target_id,
                    "role_graph_nodes": list(role_graph.get("nodes") or []),
                    "role_graph_edges": list(role_graph.get("edges") or []),
                    "evidence_status": "static_only",
                    "blockers": ["role_reader_or_event_history_required"],
                },
            }
        )


def _read_json(context: PhaseContext, phase_id: str, name: str) -> dict:
    uri = context.artifact_store.uri(context.target.target_id, phase_id, name)
    payload = context.artifact_store.read_artifact(uri)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON artifact for {phase_id}/{name}")
    return payload


def _admin_candidates(role_graph: dict) -> list[dict]:
    nodes = role_graph.get("nodes") or []
    return [node for node in nodes if node.get("kind") in {"owner_like", "role_like"}]


def _nomad_state_result(
    context: PhaseContext,
    source_manifest: dict,
    role_graph: dict,
    source_truth: dict,
    nomad_review: dict,
) -> PhaseResult:
    analysis = build_nomad_root_proof_analysis(source_manifest)
    return PhaseResult.completed(
        json_artifacts={
            "admin-state.json": {
                "status": "protocol_specific_admin_state_not_required",
                "target_id": context.target.target_id,
                "admin_candidates": _admin_candidates(role_graph),
                "source_truth_review_count": source_truth.get("review_count", 0),
                "runtime_runner": nomad_review.get("runtime_runner"),
                "evidence_status": "static_only",
                "note": "Nomad historical replay is message-authentication state, not admin initializer state.",
                "blockers": [],
            },
            "proxy-state.json": {
                "status": "historical_bridge_proxy_context_ready",
                "target_id": context.target.target_id,
                "proxy_context": dict(source_manifest.get("proxy_context") or {}),
                "historical_proxy": analysis.get("historical_replica_proxy"),
                "fork_block_number": NOMAD_EXPLOIT_FORK_BLOCK,
                "evidence_status": "static_only",
                "note": "Current proxy implementation/state is not claimed by this historical replay.",
                "blockers": [],
            },
            "role-state.json": {
                "status": "protocol_actor_model_ready",
                "target_id": context.target.target_id,
                "role_graph_nodes": list(role_graph.get("nodes") or []),
                "role_graph_edges": list(role_graph.get("edges") or []),
                "actor_model": nomad_review.get("actor_model") or "any_external_caller_with_forged_nomad_message",
                "reader": nomad_review.get("measurable_reader"),
                "delta": nomad_review.get("measurable_delta"),
                "evidence_status": "static_only",
                "note": "Actor model is for local historical fork reproduction only.",
                "blockers": [],
            },
            "bridge-state-review.json": {
                "status": "historical_fork_state_ready_current_live_not_claimed",
                "target_id": context.target.target_id,
                "runtime_runner": nomad_review.get("runtime_runner"),
                "fork_block_number": NOMAD_EXPLOIT_FORK_BLOCK,
                "root_proof_model": analysis.get("root_proof_model"),
                "message_plan": analysis.get("message_plan"),
                "runtime_assertions": analysis.get("runtime_assertions"),
                "current_state_review": analysis.get("current_state_review"),
                "evidence_status": "static_only",
                "blockers": [],
            },
        }
    )


def _verified_initializer_review(source_truth: dict) -> dict | None:
    return _verified_runtime_review(
        source_truth,
        {
            "initializer_runtime",
            "access_control_initializer_runtime",
            "proxy_storage_collision_runtime",
            "wormhole_implementation_runtime",
            "nomad_bridge_root_proof_runtime",
            "furucombo_delegatecall_runtime",
            "alchemix_keeper_runtime",
        },
    )


def _verified_runtime_review(source_truth: dict, runners: set[str]) -> dict | None:
    for review in source_truth.get("reviews") or []:
        if review.get("source_truth_verified") is not True:
            continue
        if review.get("runtime_runner") in runners:
            return review
    return None
