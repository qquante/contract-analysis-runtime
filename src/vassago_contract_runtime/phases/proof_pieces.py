"""Phase 07 proof-piece readiness adapter."""

from __future__ import annotations

from typing import Any

from vassago_contract_runtime.design_runtime.models import short_hash
from vassago_contract_runtime.design_runtime.runner import PhaseContext, PhaseResult


class ProofPiecesAdapter:
    """Consolidate source/state proof pieces before compile or runtime.

    This phase is deliberately conservative. It can mark a candidate as
    compile-ready only when all non-compile proof pieces are present. It cannot
    promote evidence and it does not call Foundry.
    """

    REQUIRED_PIECES = (
        "source_truth_guard_gap",
        "actor_model",
        "codable_args",
        "measurable_reader",
        "measurable_delta",
        "explicit_predicate",
    )

    def run(self, context: PhaseContext) -> PhaseResult:
        source_truth = _read_json(context, "05_source_truth", "sc01-source-truth.json")
        admin_state = _read_optional_json(context, "06_onchain_state", "admin-state.json")
        proxy_state = _read_optional_json(context, "06_onchain_state", "proxy-state.json")
        role_state = _read_optional_json(context, "06_onchain_state", "role-state.json")
        reviews = list(source_truth.get("reviews") or [])
        pieces = [_proof_piece(review, admin_state, proxy_state, role_state) for review in reviews]
        hypotheses = [_hypothesis(piece) for piece in pieces if piece["non_compile_pieces_complete"]]
        runtime_ready = [item for item in hypotheses if item["runtime_ready"]]
        compile_ready = [item for item in hypotheses if item["compile_ready"]]
        status = "ready" if runtime_ready else "blocked"
        blockers = _blockers(pieces)
        return PhaseResult.completed(
            json_artifacts={
                "sc01-proof-piece-state.json": {
                    "status": status,
                    "target_id": context.target.target_id,
                    "proof_piece_count": len(pieces),
                    "compile_ready_count": len(compile_ready),
                    "runtime_ready_count": len(runtime_ready),
                    "pieces": pieces,
                    "evidence_status": "static_only",
                    "blockers": blockers,
                },
                "sc01-exploit-hypotheses.json": {
                    "status": "candidate_only" if hypotheses else "blocked",
                    "target_id": context.target.target_id,
                    "hypothesis_count": len(hypotheses),
                    "hypotheses": hypotheses,
                    "evidence_status": "candidate" if hypotheses else "static_only",
                    "blockers": [] if hypotheses else blockers,
                },
                "sc01-runtime-ready.json": {
                    "status": status,
                    "target_id": context.target.target_id,
                    "foundry_allowed": bool(runtime_ready),
                    "compile_ready_count": len(compile_ready),
                    "runtime_ready_count": len(runtime_ready),
                    "ready_hypothesis_ids": [item["hypothesis_id"] for item in runtime_ready],
                    "compile_ready_hypothesis_ids": [item["hypothesis_id"] for item in compile_ready],
                    "evidence_status": "static_only",
                    "blockers": blockers,
                    "policy": {
                        "no_broadcast": True,
                        "local_runtime_only": True,
                        "requires_compile_only_pass": True,
                        "requires_explicit_runtime_authorization": True,
                    },
                },
            }
        )


def _read_json(context: PhaseContext, phase_id: str, name: str) -> dict:
    uri = context.artifact_store.uri(context.target.target_id, phase_id, name)
    payload = context.artifact_store.read_artifact(uri)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON artifact for {phase_id}/{name}")
    return payload


def _read_optional_json(context: PhaseContext, phase_id: str, name: str) -> dict:
    try:
        return _read_json(context, phase_id, name)
    except Exception:
        return {"status": "missing", "blockers": [f"{phase_id}/{name}_missing"]}


def _proof_piece(review: dict[str, Any], admin_state: dict, proxy_state: dict, role_state: dict) -> dict[str, Any]:
    raw_missing = review.get("missing_proof_pieces")
    missing = set(raw_missing if raw_missing is not None else ProofPiecesAdapter.REQUIRED_PIECES)
    state_blockers = []
    for state in (admin_state, proxy_state, role_state):
        state_blockers.extend(state.get("blockers") or [])
    verified = review.get("source_truth_verified") is True
    if not verified:
        missing.add("source_truth_guard_gap")
    if state_blockers:
        missing.add("measurable_reader")
        missing.add("measurable_delta")
    complete = verified and not missing
    return {
        "proof_piece_id": f"PP-{short_hash(str(review.get('source_truth_id')))}",
        "source_truth_id": review.get("source_truth_id"),
        "queue_id": review.get("queue_id"),
        "candidate_id": review.get("candidate_id"),
        "thesis_id": review.get("thesis_id"),
        "source_truth_verified": verified,
        "non_compile_pieces_complete": complete,
        "present_pieces": sorted(set(ProofPiecesAdapter.REQUIRED_PIECES) - missing),
        "missing_pieces": sorted(missing),
        "state_blockers": sorted(set(str(item) for item in state_blockers)),
        "evidence_refs": list(review.get("evidence_refs") or []),
    }


def _hypothesis(piece: dict[str, Any]) -> dict[str, Any]:
    hypothesis_id = f"SC01H-{short_hash(piece['proof_piece_id'])}"
    return {
        "hypothesis_id": hypothesis_id,
        "proof_piece_id": piece["proof_piece_id"],
        "candidate_id": piece.get("candidate_id"),
        "thesis_id": piece.get("thesis_id"),
        "compile_ready": True,
        "runtime_ready": True,
        "runtime_blockers": ["compile_only_not_run", "explicit_runtime_authorization_required"],
        "evidence_status": "candidate",
    }


def _blockers(pieces: list[dict[str, Any]]) -> list[str]:
    if not pieces:
        return ["no_source_truth_reviews"]
    if any(piece.get("non_compile_pieces_complete") for piece in pieces):
        return ["compile_only_not_run", "explicit_runtime_authorization_required"]
    blockers = set()
    for piece in pieces:
        blockers.update(piece.get("missing_pieces") or [])
        blockers.update(piece.get("state_blockers") or [])
    blockers.add("compile_only_not_ready")
    blockers.add("runtime_not_ready")
    return sorted(str(item) for item in blockers)
