"""Phase 06 on-chain state skeleton adapter."""

from __future__ import annotations

from vassago_contract_runtime.design_runtime.runner import PhaseContext, PhaseResult
from vassago_contract_runtime.sc01_source import evaluate_uninitialized_uups_initializer


class OnChainStateAdapter:
    """Prepare on-chain state sidecars without doing RPC by default."""

    def run(self, context: PhaseContext) -> PhaseResult:
        source_manifest = _read_json(context, "01_dossier", "source-manifest.json")
        role_graph = _read_json(context, "02_semantic_surface", "role-graph.json")
        source_truth = _read_json(context, "05_source_truth", "sc01-source-truth.json")
        proxy_context = dict(source_manifest.get("proxy_context") or {})
        if _is_local_positive_fixture(source_manifest, source_truth):
            return PhaseResult.completed(
                json_artifacts={
                    "admin-state.json": {
                        "status": "fixture_state_ready",
                        "target_id": context.target.target_id,
                        "admin_candidates": _admin_candidates(role_graph),
                        "source_truth_review_count": source_truth.get("review_count", 0),
                        "reader": "owner()",
                        "initial_value": "address(0)",
                        "post_condition": "owner() == unauthorized caller after initialize()",
                        "evidence_status": "static_only",
                        "blockers": [],
                    },
                    "proxy-state.json": {
                        "status": "fixture_proxy_context_ready",
                        "target_id": context.target.target_id,
                        "proxy_context": proxy_context,
                        "has_proxy_hint": False,
                        "note": "Local fixture models implementation-local initialization impact; no live proxy is claimed.",
                        "evidence_status": "static_only",
                        "blockers": [],
                    },
                    "role-state.json": {
                        "status": "fixture_role_state_ready",
                        "target_id": context.target.target_id,
                        "role_graph_nodes": list(role_graph.get("nodes") or []),
                        "role_graph_edges": list(role_graph.get("edges") or []),
                        "actor_model": "any_external_caller",
                        "evidence_status": "static_only",
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


def _is_local_positive_fixture(source_manifest: dict, source_truth: dict) -> bool:
    return (
        source_manifest.get("provider") == "fixture"
        and evaluate_uninitialized_uups_initializer(source_manifest).get("verified") is True
        and int(source_truth.get("source_truth_verified_count") or 0) > 0
    )
