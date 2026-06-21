"""Phase 02 semantic surface skeleton adapter."""

from __future__ import annotations

import re
from typing import Any

from vassago_contract_runtime.design_runtime.models import short_hash
from vassago_contract_runtime.design_runtime.runner import PhaseContext, PhaseResult


class SemanticSurfaceAdapter:
    """Build a static semantic surface from ABI and local source.

    This is not source truth. It produces structured hints that later phases
    must validate through stronger adapters.
    """

    def run(self, context: PhaseContext) -> PhaseResult:
        function_index = _read_json(context, "01_dossier", "function-index.json")
        source_manifest = _read_json(context, "01_dossier", "source-manifest.json")
        functions = [_surface_function(item, source_manifest) for item in function_index.get("functions", [])]
        guards = [_guard_for(function) for function in functions]
        writes = _state_write_map(functions)
        role_graph = _role_graph(functions, source_manifest)
        semantic_roles = [_semantic_role(function) for function in functions]
        return PhaseResult.completed(
            json_artifacts={
                "access-surface.json": {
                    "status": "completed",
                    "target_id": context.target.target_id,
                    "function_count": len(functions),
                    "functions": functions,
                    "evidence_status": "static_only",
                    "extraction_sources": ["abi", "local_source_heuristic"],
                    "warning": "Static semantic surface. Later source-truth phase must validate any candidate.",
                },
                "semantic-map.json": {
                    "status": "candidate_only",
                    "target_id": context.target.target_id,
                    "roles": semantic_roles,
                    "evidence_status": "static_only",
                },
                "guard-map.json": {
                    "status": "candidate_only",
                    "target_id": context.target.target_id,
                    "guards": guards,
                    "evidence_status": "static_only",
                },
                "state-write-map.json": {
                    "status": "candidate_only",
                    "target_id": context.target.target_id,
                    "state_variables": writes,
                    "evidence_status": "static_only",
                },
                "role-graph.json": role_graph,
            }
        )


def _read_json(context: PhaseContext, phase_id: str, name: str) -> dict:
    uri = context.artifact_store.uri(context.target.target_id, phase_id, name)
    payload = context.artifact_store.read_artifact(uri)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON artifact for {phase_id}/{name}")
    return payload


def _surface_function(function: dict[str, Any], source_manifest: dict[str, Any]) -> dict[str, Any]:
    name = str(function.get("name") or "")
    inputs = list(function.get("inputs") or [])
    signature = f"{name}({','.join(str(item.get('type') or '') for item in inputs)})"
    body = _find_function_body(name, source_manifest)
    return {
        "function_id": f"FN-{short_hash(signature)}",
        "name": name,
        "signature": signature,
        "selector": None,
        "selector_status": "not_calculated_without_keccak",
        "stateMutability": function.get("stateMutability"),
        "inputs": inputs,
        "outputs": list(function.get("outputs") or []),
        "source_excerpt": body[:2000],
        "source_status": "found" if body else "not_found",
        "guard_signals": _guard_signals(body),
        "state_write_signals": _write_signals(body),
        "call_signals": _call_signals(body),
        "extraction_source": "abi_source_heuristic" if body else "abi_only",
        "confidence": "medium" if body else "low",
    }


def _find_function_body(name: str, source_manifest: dict[str, Any]) -> str:
    if not name:
        return ""
    for source in (source_manifest.get("source_files") or {}).values():
        text = str(source)
        match = re.search(rf"function\s+{re.escape(name)}\s*\([^)]*\)(?P<body>[\s\S]{{0,2400}})", text)
        if match:
            return match.group(0)
    return ""


def _guard_signals(body: str) -> list[str]:
    signals = []
    checks = {
        "msg_sender_check": "msg.sender",
        "tx_origin_check": "tx.origin",
        "role_check": "hasRole",
        "owner_check": "owner",
        "initializer_check": "initializer",
        "upgrade_check": "_authorizeUpgrade",
    }
    for signal, marker in checks.items():
        if marker in body:
            signals.append(signal)
    if "require(" in body or "revert " in body or "if (" in body:
        signals.append("inline_condition")
    return sorted(set(signals))


def _write_signals(body: str) -> list[str]:
    if not body:
        return []
    candidates = re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*(?:=|\+=|-=|\*=|/=)", body)
    excluded = {"if", "require", "return", "for", "while", "uint", "uint256", "address", "bool", "string"}
    return sorted({item for item in candidates if item not in excluded})


def _call_signals(body: str) -> list[str]:
    calls = re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", body)
    excluded = {"if", "for", "while", "require", "revert", "function", "return"}
    return sorted({item for item in calls if item not in excluded})


def _guard_for(function: dict[str, Any]) -> dict[str, Any]:
    signals = set(function.get("guard_signals") or [])
    if "tx_origin_check" in signals:
        guard_class = "tx_origin_authorization"
    elif "role_check" in signals:
        guard_class = "role"
    elif "owner_check" in signals or "msg_sender_check" in signals:
        guard_class = "owner_or_sender"
    elif "inline_condition" in signals:
        guard_class = "custom_or_unknown"
    else:
        guard_class = "none"
    return {
        "function_id": function["function_id"],
        "function": function["signature"],
        "guard_class": guard_class,
        "signals": sorted(signals),
        "confidence": function["confidence"],
    }


def _semantic_role(function: dict[str, Any]) -> dict[str, Any]:
    name = str(function.get("name") or "").lower()
    signals = set(function.get("guard_signals") or [])
    role = "unknown"
    if "initialize" in name or "initializer_check" in signals:
        role = "initializer"
    elif "upgrade" in name or "upgrade_check" in signals:
        role = "implementation_upgrade"
    elif "grantrole" in name or "revokerole" in name:
        role = "role_lifecycle"
    return {
        "function_id": function["function_id"],
        "function": function["signature"],
        "semantic_role": role,
        "status": "candidate_only" if role != "unknown" else "unknown",
        "evidence_refs": ["abi", "source_excerpt"] if function.get("source_excerpt") else ["abi"],
    }


def _state_write_map(functions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_variable: dict[str, list[dict[str, str]]] = {}
    for function in functions:
        for variable in function.get("state_write_signals") or []:
            by_variable.setdefault(variable, []).append(
                {"function_id": function["function_id"], "function": function["signature"]}
            )
    return [
        {
            "variable": variable,
            "writers": writers,
            "writer_count": len(writers),
            "status": "candidate_only",
        }
        for variable, writers in sorted(by_variable.items())
    ]


def _role_graph(functions: list[dict[str, Any]], source_manifest: dict[str, Any]) -> dict[str, Any]:
    source_text = " ".join(str(value) for value in (source_manifest.get("source_files") or {}).values())
    nodes = []
    edges = []
    if "owner" in source_text:
        nodes.append({"id": "owner", "kind": "owner_like", "status": "candidate_only"})
    if "hasRole" in source_text or "grantRole" in source_text:
        nodes.append({"id": "access_control_role", "kind": "role_like", "status": "candidate_only"})
    for function in functions:
        if "role_check" in set(function.get("guard_signals") or []):
            edges.append({"from": "access_control_role", "to": function["signature"], "kind": "guards"})
        elif "owner_check" in set(function.get("guard_signals") or []):
            edges.append({"from": "owner", "to": function["signature"], "kind": "guards"})
    return {
        "status": "candidate_only",
        "nodes": nodes,
        "edges": edges,
        "evidence_status": "static_only",
    }
