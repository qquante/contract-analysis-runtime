"""Phase 01 dossier skeleton adapter."""

from __future__ import annotations

import re
from pathlib import Path

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
    source_files = source.get("source_files") or {}
    if source_files:
        metadata = dict(source.get("metadata") or {})
        selected_source_file = _select_source_file(source_files, metadata)
        compiler = source.get("compiler") or {}
        compiler_version = _normalize_solc_version(compiler.get("version"))
        pragma_constraints = _pragma_constraints(source_files)
        selected_version = compiler_version or _first_pragma_version(pragma_constraints)
        solc_remaps = _infer_solc_remaps(source_files)
        return {
            "status": "available",
            "source_status": source.get("status"),
            "provider": source.get("provider"),
            "compiler": compiler,
            "compiler_version": compiler_version,
            "pragma_constraints": pragma_constraints,
            "selected_source_file": selected_source_file,
            "target_contract": metadata.get("contract_name"),
            "source_file_count": len(source_files),
            "solc_remaps": solc_remaps,
            "solc_version_selection": {
                "requested_version": selected_version,
                "source": "compiler_metadata" if compiler_version else "pragma_constraint" if selected_version else "unknown",
                "env_var": "SOLC_VERSION" if selected_version else None,
                "status": "selected" if selected_version else "not_selected",
            },
            "blockers": [],
        }
    return {
        "status": "missing_source",
        "source_status": source.get("status"),
        "provider": source.get("provider"),
        "compiler": source.get("compiler") or {},
        "source_file_count": 0,
        "blockers": ["compile_context_requires_source_bundle"],
    }


def _select_source_file(source_files: dict[str, str], metadata: dict) -> str:
    explicit = str(metadata.get("selected_source_file") or "").strip()
    if explicit and explicit in source_files:
        return explicit

    contract_name = str(metadata.get("contract_name") or "").strip()
    if contract_name:
        declaration = re.compile(
            rf"\b(?:abstract\s+contract|contract|interface|library)\s+{re.escape(contract_name)}\b"
        )
        matches = [
            filename
            for filename, content in sorted(source_files.items())
            if declaration.search(str(content))
        ]
        if matches:
            return matches[0]

    return sorted(source_files)[0]


def _normalize_solc_version(value: object) -> str:
    text = str(value or "")
    match = re.search(r"v?(0\.\d+\.\d+)", text)
    return match.group(1) if match else ""


def _pragma_constraints(source_files: dict[str, str]) -> list[str]:
    constraints: list[str] = []
    for content in source_files.values():
        for match in re.finditer(r"pragma\s+solidity\s+([^;]+);", str(content)):
            constraints.append(" ".join(match.group(1).split()))
    return sorted(set(constraints))


def _first_pragma_version(constraints: list[str]) -> str:
    for constraint in constraints:
        match = re.search(r"(0\.\d+\.\d+)", constraint)
        if match:
            return match.group(1)
    return ""


def _infer_solc_remaps(source_files: dict[str, str]) -> list[str]:
    remaps: set[str] = set()
    for name in source_files:
        parts = Path(name).as_posix().split("/")
        for index, part in enumerate(parts[:-1]):
            if part != "lib" or index + 1 >= len(parts):
                continue
            package = parts[index + 1]
            if not package or package in {"src", "test", "script"}:
                continue
            prefix = "/".join(parts[: index + 2])
            remaps.add(f"{package}/={prefix}/")
    return sorted(remaps)
