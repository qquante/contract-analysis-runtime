"""Phase 01 dossier skeleton adapter."""

from __future__ import annotations

from vassago_contract_runtime.contracts import ContractTargetRef, NullSourceResolver, SourceResolver
from vassago_contract_runtime.design_runtime.runner import PhaseContext, PhaseResult


class DossierAdapter:
    """Build a source-aware dossier skeleton without network by default."""

    def __init__(self, source_resolver: SourceResolver | None = None) -> None:
        self.source_resolver = source_resolver or NullSourceResolver()

    def run(self, context: PhaseContext) -> PhaseResult:
        target = ContractTargetRef.from_target(context.target)
        source = self.source_resolver.resolve(target)
        function_index = _function_index(source.to_json())
        protocol_fingerprint = _protocol_fingerprint(source.to_json())
        compile_context = _compile_context(source.to_json())
        dossier = {
            "status": "skeleton",
            "phase_id": context.phase.phase_id,
            "target": target.to_json(),
            "source_resolution": source.to_json(),
            "function_count": len(function_index["functions"]),
            "evidence_status": "static_only",
            "note": "Dossier skeleton. No Explorer/RPC/Slither/Foundry provider was used.",
        }
        return PhaseResult.completed(
            json_artifacts={
                "scan-dossier.json": dossier,
                "function-index.json": function_index,
                "source-manifest.json": source.to_json(),
                "compile-context.json": compile_context,
                "protocol-fingerprint.json": protocol_fingerprint,
            }
        )


def _function_index(source: dict) -> dict:
    abi = source.get("abi") or []
    functions = []
    events = []
    for item in abi:
        if item.get("type") == "function":
            functions.append(
                {
                    "name": item.get("name"),
                    "stateMutability": item.get("stateMutability"),
                    "inputs": item.get("inputs", []),
                    "outputs": item.get("outputs", []),
                    "semantic_role": "unknown",
                    "semantic_status": "abi_inventory_only",
                }
            )
        elif item.get("type") == "event":
            events.append({"name": item.get("name"), "inputs": item.get("inputs", [])})
    return {
        "status": "completed",
        "source_status": source.get("status"),
        "functions": functions,
        "events": events,
        "function_count": len(functions),
        "event_count": len(events),
    }


def _protocol_fingerprint(source: dict) -> dict:
    return {
        "status": "candidate_only",
        "source_status": source.get("status"),
        "families": [],
        "blockers": ["protocol_fingerprint_requires_source_or_abi"],
        "evidence_status": "static_only",
    }


def _compile_context(source: dict) -> dict:
    return {
        "status": "missing_source",
        "source_status": source.get("status"),
        "provider": source.get("provider"),
        "compiler": source.get("compiler") or {},
        "source_file_count": len(source.get("source_files") or {}),
        "blockers": ["compile_context_requires_source_bundle"],
    }
