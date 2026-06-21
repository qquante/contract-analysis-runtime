"""Phase 03 corpus motif skeleton adapter."""

from __future__ import annotations

from vassago_contract_runtime.corpus import CorpusAdapter, CorpusScanContext, DesignCorpusAdapter, NullCorpusAdapter
from vassago_contract_runtime.design_runtime.runner import PhaseContext, PhaseResult


class CorpusMotifsAdapter:
    """Build thesis candidates from the local design corpus.

    The adapter only reads previous static artifacts and local corpus YAMLs.
    It does not call LLMs, Explorer, RPC, Slither or Foundry.
    """

    def __init__(self, corpus_adapter: CorpusAdapter | None = None) -> None:
        self.corpus_adapter = corpus_adapter or NullCorpusAdapter()

    @classmethod
    def from_design_dir(cls, design_dir: str) -> "CorpusMotifsAdapter":
        return cls(DesignCorpusAdapter.from_dir(f"{design_dir}/corpus"))

    def run(self, context: PhaseContext) -> PhaseResult:
        function_index = _read_json(context, "01_dossier", "function-index.json")
        source_manifest = _read_json(context, "01_dossier", "source-manifest.json")
        protocol_fingerprint = _read_json(context, "01_dossier", "protocol-fingerprint.json")
        scan_context = CorpusScanContext(
            design_id=context.design.design_id,
            target_id=context.target.target_id,
            chain=context.target.chain,
            address=context.target.address,
            function_index=function_index,
            source_manifest=source_manifest,
            protocol_fingerprint=protocol_fingerprint,
        )
        result = self.corpus_adapter.scan(scan_context)
        candidates = [_candidate(match, context) for match in result.matches]
        return PhaseResult.completed(
            json_artifacts={
                "sc01-corpus-matches.json": result.to_json(),
                "sc01-thesis-candidates.json": {
                    "status": "candidate_only" if candidates else "no_matches",
                    "candidate_count": len(candidates),
                    "candidates": candidates,
                    "evidence_status": "static_only",
                    "note": "Corpus motif candidates are routing hints only; they do not prove vulnerability.",
                },
            }
        )


def _read_json(context: PhaseContext, phase_id: str, name: str) -> dict:
    uri = context.artifact_store.uri(context.target.target_id, phase_id, name)
    payload = context.artifact_store.read_artifact(uri)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON artifact for {phase_id}/{name}")
    return payload


def _candidate(match: object, context: PhaseContext) -> dict:
    payload = match.to_json()
    return {
        "candidate_id": f"TC-{context.target.target_id[3:]}-{payload['thesis_id']}",
        "target_id": context.target.target_id,
        "chain": context.target.chain,
        "address": context.target.address,
        "thesis_id": payload["thesis_id"],
        "corpus_id": payload["corpus_id"],
        "bug_family": payload["bug_family"],
        "status": "candidate_only",
        "matched_motifs": payload["matched_motifs"],
        "matched_functions": payload["matched_functions"],
        "evidence_refs": payload["evidence_refs"],
        "blockers": ["source_truth_not_run", "onchain_state_not_read", "proof_pieces_not_built"],
    }
