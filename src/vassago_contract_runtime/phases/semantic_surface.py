"""Phase 02 semantic surface skeleton adapter."""

from __future__ import annotations

import re
from typing import Any

from vassago_contract_runtime.design_runtime.models import short_hash
from vassago_contract_runtime.design_runtime.runner import PhaseContext, PhaseResult
from vassago_contract_runtime.slither import SlitherAdapter, SlitherInput


class SemanticSurfaceAdapter:
    """Build a static semantic surface from ABI and local source.

    This is not source truth. It produces structured hints that later phases
    must validate through stronger adapters.
    """

    def __init__(self, slither: SlitherAdapter | None = None) -> None:
        self.slither = slither

    def run(self, context: PhaseContext) -> PhaseResult:
        function_index = _read_json(context, "01_dossier", "function-index.json")
        source_manifest = _read_json(context, "01_dossier", "source-manifest.json")
        compile_context = _read_json(context, "01_dossier", "compile-context.json")
        slither_context = _slither_context(context, source_manifest, compile_context, self.slither)
        slither_functions = _slither_functions(slither_context)
        functions = [
            _surface_function(item, source_manifest, slither_functions)
            for item in function_index.get("functions", [])
        ]
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
                    "extraction_sources": _extraction_sources(functions),
                    "slither": _slither_summary(slither_context),
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


def _slither_context(
    context: PhaseContext,
    source_manifest: dict[str, Any],
    compile_context: dict[str, Any],
    slither: SlitherAdapter | None,
) -> dict[str, Any]:
    manifest_ir = _manifest_slither_ir(source_manifest)
    if manifest_ir:
        return {
            "status": "completed",
            "provider": "source_manifest",
            "ir": manifest_ir,
            "detectors": [],
            "error": None,
        }
    source_files = dict(source_manifest.get("source_files") or {})
    if compile_context.get("status") != "available":
        return {
            "status": "skipped",
            "provider": "not_invoked",
            "ir": {},
            "detectors": [],
            "error": {"code": "compile_context_unavailable", "message": "No compile context available."},
        }
    if slither is None:
        return {
            "status": "skipped",
            "provider": "not_configured",
            "ir": {},
            "detectors": [],
            "error": {"code": "slither_adapter_not_configured", "message": "No Slither adapter configured."},
        }
    result = slither.analyze(
        SlitherInput(
            target_id=context.target.target_id,
            source_files=source_files,
            compile_context=compile_context,
            target_contract=compile_context.get("target_contract"),
        )
    )
    payload = result.to_json()
    return {
        "status": payload.get("status"),
        "provider": payload.get("provider"),
        "ir": payload.get("ir") or {},
        "detectors": payload.get("detectors") or [],
        "error": payload.get("error"),
        "metadata": payload.get("metadata") or {},
    }


def _manifest_slither_ir(source_manifest: dict[str, Any]) -> dict[str, Any]:
    metadata = dict(source_manifest.get("metadata") or {})
    for key in ("slither_ir", "slither_surface"):
        value = metadata.get(key)
        if isinstance(value, dict):
            return value
    value = source_manifest.get("slither_ir")
    return value if isinstance(value, dict) else {}


def _slither_functions(slither_context: dict[str, Any]) -> dict[str, dict[str, Any]]:
    ir = slither_context.get("ir") if isinstance(slither_context, dict) else {}
    if not isinstance(ir, dict):
        return {}
    functions = ir.get("functions")
    if not isinstance(functions, list):
        contracts = ir.get("contracts")
        functions = []
        if isinstance(contracts, list):
            for contract in contracts:
                if isinstance(contract, dict) and isinstance(contract.get("functions"), list):
                    functions.extend(contract["functions"])
    indexed: dict[str, dict[str, Any]] = {}
    for item in functions or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        signature = str(item.get("signature") or item.get("full_name") or "").strip()
        if signature:
            indexed[signature] = item
        if name:
            indexed.setdefault(name, item)
    return indexed


def _surface_function(
    function: dict[str, Any],
    source_manifest: dict[str, Any],
    slither_functions: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    name = str(function.get("name") or "")
    inputs = list(function.get("inputs") or [])
    signature = f"{name}({','.join(str(item.get('type') or '') for item in inputs)})"
    slither_function = slither_functions.get(signature) or slither_functions.get(name)
    if slither_function:
        return _surface_function_from_slither(function, signature, slither_function, source_manifest)
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


def _surface_function_from_slither(
    function: dict[str, Any],
    signature: str,
    slither_function: dict[str, Any],
    source_manifest: dict[str, Any],
) -> dict[str, Any]:
    name = str(function.get("name") or slither_function.get("name") or "")
    body = str(slither_function.get("source_excerpt") or slither_function.get("source") or "")
    if not body:
        body = _find_function_body(name, source_manifest)
    modifiers = _string_list(slither_function, "modifiers")
    state_writes = _string_list(slither_function, "state_writes", "state_write_signals", "writes")
    calls = _string_list(slither_function, "calls", "internal_calls", "external_calls", "call_signals")
    guard_signals = sorted(set(_guard_signals(body) + _guard_signals_from_slither(slither_function)))
    return {
        "function_id": f"FN-{short_hash(signature)}",
        "name": name,
        "signature": signature,
        "selector": None,
        "selector_status": "not_calculated_without_keccak",
        "stateMutability": function.get("stateMutability") or slither_function.get("stateMutability"),
        "inputs": list(function.get("inputs") or []),
        "outputs": list(function.get("outputs") or []),
        "source_excerpt": body[:2000],
        "source_status": "found" if body else "not_found",
        "guard_signals": guard_signals,
        "state_write_signals": sorted(set(state_writes or _write_signals(body))),
        "call_signals": sorted(set(calls or _call_signals(body))),
        "modifiers": modifiers,
        "slither_refs": list(slither_function.get("evidence_refs") or []),
        "extraction_source": "slither_ir",
        "confidence": "high",
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


def _guard_signals_from_slither(function: dict[str, Any]) -> list[str]:
    signals = []
    values = " ".join(_string_list(function, "modifiers", "requires", "conditions", "guards")).lower()
    if "tx.origin" in values:
        signals.append("tx_origin_check")
    if "hasrole" in values or "onlyrole" in values or "accesscontrol" in values:
        signals.append("role_check")
    if "owner" in values or "onlyowner" in values or "msg.sender" in values:
        signals.append("owner_check")
    if "initializer" in values:
        signals.append("initializer_check")
    if "_authorizeupgrade" in values:
        signals.append("upgrade_check")
    if values and any(marker in values for marker in ("require", "revert", "only", "guard")):
        signals.append("inline_condition")
    return sorted(set(signals))


def _string_list(payload: dict[str, Any], *keys: str) -> list[str]:
    values: list[str] = []
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    text = item.get("name") or item.get("canonical_name") or item.get("variable") or item.get("signature")
                    if text:
                        values.append(str(text))
                elif item is not None:
                    values.append(str(item))
        elif isinstance(value, str):
            values.append(value)
    return sorted({item for item in values if item})


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


def _extraction_sources(functions: list[dict[str, Any]]) -> list[str]:
    sources = {"abi"}
    sources.update(str(function.get("extraction_source") or "unknown") for function in functions)
    return sorted(sources)


def _slither_summary(slither_context: dict[str, Any]) -> dict[str, Any]:
    ir = slither_context.get("ir") if isinstance(slither_context, dict) else {}
    functions = _slither_functions(slither_context)
    detectors = slither_context.get("detectors") if isinstance(slither_context, dict) else []
    metadata = slither_context.get("metadata") if isinstance(slither_context, dict) else {}
    compiler_selection = metadata.get("compiler_selection") if isinstance(metadata, dict) else None
    return {
        "status": slither_context.get("status"),
        "provider": slither_context.get("provider"),
        "function_count": len(functions),
        "detector_count": len(detectors) if isinstance(detectors, list) else 0,
        "ir_status": ir.get("status") if isinstance(ir, dict) else None,
        "compiler_selection": compiler_selection,
        "error": slither_context.get("error"),
    }
