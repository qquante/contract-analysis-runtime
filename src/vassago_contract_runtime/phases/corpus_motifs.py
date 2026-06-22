"""Phase 03 corpus motif skeleton adapter."""

from __future__ import annotations

from vassago_contract_runtime.corpus import CorpusAdapter, CorpusScanContext, DesignCorpusAdapter, NullCorpusAdapter
from vassago_contract_runtime.design_runtime.runner import PhaseContext, PhaseResult
from vassago_contract_runtime.sc01_proxy_acquisition import build_proxy_upgrade_candidates


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
        access_surface = _read_json(context, "02_semantic_surface", "access-surface.json")
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
        candidates = [
            candidate
            for candidate in (_candidate(match, context, access_surface) for match in result.matches)
            if candidate is not None
        ]
        candidates = _dedupe_candidates(
            candidates
            + build_proxy_upgrade_candidates(
                target_id=context.target.target_id,
                chain=context.target.chain,
                address=context.target.address,
                function_index=function_index,
                source_manifest=source_manifest,
                access_surface=access_surface,
            )
        )
        return PhaseResult.completed(
            json_artifacts={
                "sc01-corpus-matches.json": result.to_json(),
                "sc01-thesis-candidates.json": {
                    "status": "candidate_only" if candidates else "no_matches",
                    "candidate_count": len(candidates),
                    "candidates": candidates,
                    "dropped_match_count": len(result.matches) - len(candidates),
                    "evidence_status": "static_only",
                    "note": "Corpus motif candidates require function-level evidence and remain routing hints only.",
                },
            }
        )


def _read_json(context: PhaseContext, phase_id: str, name: str) -> dict:
    uri = context.artifact_store.uri(context.target.target_id, phase_id, name)
    payload = context.artifact_store.read_artifact(uri)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON artifact for {phase_id}/{name}")
    return payload


def _candidate(match: object, context: PhaseContext, access_surface: dict) -> dict | None:
    payload = match.to_json()
    matched_functions = _surface_functions_for_motifs(access_surface, payload["matched_motifs"], payload["matched_functions"])
    if not matched_functions:
        return None
    if payload["thesis_id"] == "proxy_storage_collision_reinitializer" and not _has_proxy_admin_function_evidence(
        access_surface,
        matched_functions,
    ):
        return None
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
        "matched_functions": matched_functions,
        "evidence_refs": sorted(set(payload["evidence_refs"] + [f"access-surface:{item}" for item in matched_functions])),
        "blockers": ["source_truth_not_run", "onchain_state_not_read", "proof_pieces_not_built"],
    }


def _dedupe_candidates(candidates: list[dict]) -> list[dict]:
    merged: dict[str, dict] = {}
    for candidate in candidates:
        key = str(candidate.get("thesis_id") or "")
        if key not in merged:
            merged[key] = dict(candidate)
            continue
        existing = merged[key]
        for field in ("matched_functions", "matched_motifs", "evidence_refs", "blockers"):
            existing[field] = sorted(
                {
                    *(str(item) for item in existing.get(field) or []),
                    *(str(item) for item in candidate.get(field) or []),
                }
            )
        existing["acquisition_source"] = "+".join(
            sorted(
                {
                    str(existing.get("acquisition_source") or "design_corpus"),
                    str(candidate.get("acquisition_source") or "design_corpus"),
                }
            )
        )
    return sorted(
        merged.values(),
        key=lambda item: (str(item.get("thesis_id") or ""), str(item.get("candidate_id") or "")),
    )


def _surface_functions_for_motifs(access_surface: dict, motifs: list[str], existing: list[str]) -> list[str]:
    motif_values = [str(item).lower() for item in motifs if str(item).strip()]
    existing_names = {str(item).split("(")[0].lower() for item in existing}
    matches: list[str] = []
    for function in access_surface.get("functions", []):
        signature = str(function.get("signature") or "")
        name = str(function.get("name") or "")
        haystack = " ".join(
            [
                signature,
                name,
                str(function.get("source_excerpt") or ""),
                " ".join(str(item) for item in function.get("guard_signals") or []),
                " ".join(str(item) for item in function.get("call_signals") or []),
                " ".join(str(item) for item in function.get("state_write_signals") or []),
            ]
        ).lower()
        if name.lower() in existing_names or any(motif in haystack for motif in motif_values):
            matches.append(signature or name)
    return sorted({item for item in matches if item})


def _has_proxy_admin_function_evidence(access_surface: dict, matched_functions: list[str]) -> bool:
    names = {str(item).split("(")[0] for item in matched_functions}
    for function in access_surface.get("functions", []):
        if str(function.get("name") or "") not in names and str(function.get("signature") or "") not in matched_functions:
            continue
        haystack = " ".join(
            [
                str(function.get("signature") or ""),
                str(function.get("source_excerpt") or ""),
                " ".join(str(item) for item in function.get("state_write_signals") or []),
                " ".join(str(item) for item in function.get("call_signals") or []),
            ]
        )
        if "proxyAdmin" in haystack:
            return True
    return False
