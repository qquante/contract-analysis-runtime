"""Semantic proposal layer for proxy/upgrade source-truth.

This module is deliberately source-backed. It models the future LLM/Hermes
agent contract as deterministic proposals that must be validated against ABI,
source bodies and proxy context before source-truth can use them.
"""

from __future__ import annotations

import re
from typing import Any

from vassago_contract_runtime.design_runtime.models import short_hash


CRITICAL_ROLE_MARKERS = (
    "owner",
    "admin",
    "governor",
    "guardian",
    "controller",
    "operator",
    "proxy",
    "implementation",
    "upgrader",
    "registry",
    "router",
    "treasury",
    "oracle",
    "role",
)


def build_proxy_upgrade_dossier(
    source_manifest: dict[str, Any],
    queue: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a compact proxy/upgrade dossier for agent proposals."""

    target_source = _source_text(source_manifest)
    implementation = _implementation_manifest(source_manifest)
    implementation_source = _source_text(implementation)
    entries = [
        _source_entry("target", source_manifest, target_source),
    ]
    if implementation:
        entries.append(_source_entry("implementation", implementation, implementation_source))
    thesis_ids = sorted({str(item.get("thesis_id") or "") for item in (queue or {}).get("queue", []) if item.get("thesis_id")})
    return {
        "kind": "proxy_upgrade_dossier",
        "status": "built",
        "proxy_context": dict(source_manifest.get("proxy_context") or {}),
        "thesis_ids": thesis_ids,
        "entries": entries,
        "summary": {
            "has_proxy_context": bool((source_manifest.get("proxy_context") or {}).get("proxy")),
            "has_related_implementation": bool(implementation),
            "initializer_count": sum(len(entry["initializers"]) for entry in entries),
            "upgrade_function_count": sum(len(entry["upgrade_functions"]) for entry in entries),
            "authorize_function_count": sum(len(entry["authorize_functions"]) for entry in entries),
            "reader_count": sum(len(entry["readers"]) for entry in entries),
        },
        "evidence_status": "static_only",
    }


def build_proxy_upgrade_semantic_proposals(dossier: dict[str, Any]) -> dict[str, Any]:
    """Generate agent-style proposals from a source-backed dossier."""

    proposals: list[dict[str, Any]] = []
    for entry in dossier.get("entries") or []:
        relation = str(entry.get("relation") or "target")
        for initializer in entry.get("initializers") or []:
            writes = list(initializer.get("critical_writes") or [])
            reader = _best_reader_for_writes(entry, writes)
            if writes and reader:
                proposals.append(
                    _proposal(
                        "initializer_semantic_mapping",
                        relation,
                        initializer["name"],
                        {
                            "semantic_role": "privileged_initializer",
                            "critical_writes": writes,
                            "measurable_reader": reader,
                            "actor_model": "unauthorized_external_initializer_caller",
                            "explicit_predicate": (
                                f"Unauthorized caller invokes {initializer['name']}(...) "
                                f"and changes {reader}."
                            ),
                        },
                        initializer.get("evidence_refs") or [],
                    )
                )
        for authorize in entry.get("authorize_functions") or []:
            if authorize.get("auth_class") == "weak_or_ambiguous":
                reader = _implementation_reader(entry, dossier)
                proposals.append(
                    _proposal(
                        "uups_authorize_upgrade_mapping",
                        relation,
                        authorize["name"],
                        {
                            "semantic_role": "upgrade_authorizer",
                            "upgrade_functions": list(entry.get("upgrade_functions") or []),
                            "measurable_reader": reader,
                            "actor_model": "unauthorized_external_upgrade_caller",
                            "explicit_predicate": (
                                "Unauthorized caller can satisfy _authorizeUpgrade "
                                "and change the implementation target."
                            ),
                        },
                        authorize.get("evidence_refs") or [],
                    )
                )
        for guard in entry.get("custom_guards") or []:
            proposals.append(
                _proposal(
                    "custom_guard_semantic_mapping",
                    relation,
                    str(guard.get("name") or ""),
                    {
                        "semantic_role": str(guard.get("semantic_role") or "custom_authorization_guard"),
                        "actor_variable": guard.get("actor_variable"),
                        "actor_model": "custom_authorized_actor",
                    },
                    guard.get("evidence_refs") or [],
                )
            )
    return {
        "kind": "proxy_upgrade_semantic_proposals",
        "status": "candidate_only" if proposals else "no_proposals",
        "proposal_count": len(proposals),
        "proposals": proposals,
        "evidence_status": "candidate",
        "warning": "Semantic proposals are routing hints only until validator accepts source/ABI evidence.",
    }


def validate_proxy_upgrade_semantic_proposals(
    dossier: dict[str, Any],
    proposals: dict[str, Any],
) -> dict[str, Any]:
    """Validate semantic proposals against source/ABI-backed dossier entries."""

    entries = {str(entry.get("relation") or "target"): entry for entry in dossier.get("entries") or []}
    results: list[dict[str, Any]] = []
    for proposal in proposals.get("proposals") or []:
        relation = str(proposal.get("source_relation") or "target")
        entry = entries.get(relation)
        result = _validate_one(entry, proposal)
        results.append(result)
    accepted = [item for item in results if item["status"] == "accepted"]
    return {
        "kind": "proxy_upgrade_proposal_validation",
        "status": "validated" if accepted else "no_validated_proposals",
        "proposal_count": len(results),
        "accepted_count": len(accepted),
        "rejected_count": len(results) - len(accepted),
        "results": results,
        "accepted_proposals": [item["proposal"] for item in accepted],
        "evidence_status": "static_only",
    }


def accepted_semantic_proposals(validation: dict[str, Any], kind: str | None = None) -> list[dict[str, Any]]:
    proposals = list(validation.get("accepted_proposals") or [])
    if kind is None:
        return proposals
    return [item for item in proposals if item.get("proposal_kind") == kind]


def _source_entry(relation: str, manifest: dict[str, Any], source: str) -> dict[str, Any]:
    abi = list(manifest.get("abi") or [])
    functions = _functions(source, abi)
    readers = _readers(source, abi)
    initializers = [_initializer_payload(fn, source) for fn in functions if _is_initializer(fn)]
    upgrade_functions = [fn["name"] for fn in functions if fn["name"] in {"upgradeTo", "upgradeToAndCall"}]
    authorize_functions = [_authorize_payload(fn) for fn in functions if fn["name"] == "_authorizeUpgrade"]
    custom_guards = _custom_guards(source)
    return {
        "relation": relation,
        "target": manifest.get("target"),
        "contract_name": (manifest.get("metadata") or {}).get("contract_name"),
        "status": manifest.get("status"),
        "function_count": len(functions),
        "functions": functions,
        "initializers": initializers,
        "upgrade_functions": upgrade_functions,
        "authorize_functions": authorize_functions,
        "readers": readers,
        "custom_guards": custom_guards,
    }


def _functions(source: str, abi: list[dict[str, Any]]) -> list[dict[str, Any]]:
    functions: dict[str, dict[str, Any]] = {}
    for item in abi:
        if item.get("type") != "function":
            continue
        name = str(item.get("name") or "")
        if not name:
            continue
        functions[name] = {
            "name": name,
            "inputs": list(item.get("inputs") or []),
            "visibility": "abi_external",
            "header": "",
            "body": "",
            "source_status": "abi_only",
        }
    for match in re.finditer(r"\bfunction\s+([A-Za-z_][A-Za-z0-9_]*)\s*\((?P<inputs>[^)]*)\)(?P<header>[^{;]*)\{", source):
        name = match.group(1)
        body = _body_at(source, match.end() - 1)
        functions[name] = {
            **functions.get(name, {"name": name, "inputs": []}),
            "header": match.group("header"),
            "body": body,
            "visibility": _visibility(match.group("header")),
            "source_status": "source_found",
        }
    return sorted(functions.values(), key=lambda item: item["name"])


def _readers(source: str, abi: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in abi:
        if item.get("type") == "function" and not item.get("inputs"):
            state = str(item.get("stateMutability") or "")
            name = str(item.get("name") or "")
            if name and state in {"view", "pure"}:
                result[name] = {"name": name, "source": "abi", "signature": f"{name}()"}
    for fn in _functions(source, []):
        if not re.search(r"\bview\b|\bpure\b", str(fn.get("header") or "")):
            continue
        if "(" not in str(fn.get("body") or ""):
            result.setdefault(fn["name"], {"name": fn["name"], "source": "source", "signature": f"{fn['name']}()"})
    return sorted(result.values(), key=lambda item: item["name"])


def _initializer_payload(function: dict[str, Any], source: str) -> dict[str, Any]:
    body = str(function.get("body") or "")
    writes = _critical_writes(body)
    return {
        "name": function["name"],
        "visibility": function.get("visibility"),
        "critical_writes": writes,
        "codable_args": _codable_args(function.get("inputs") or []),
        "unsupported_args": _unsupported_args(function.get("inputs") or []),
        "evidence_refs": [
            f"source:function {function['name']}",
            *[f"source:critical write {item}" for item in writes],
            *([] if "_disableInitializers" not in source else ["source:_disableInitializers"]),
        ],
    }


def _authorize_payload(function: dict[str, Any]) -> dict[str, Any]:
    body = f"{function.get('header') or ''}\n{function.get('body') or ''}"
    return {
        "name": function["name"],
        "auth_class": _auth_class(body),
        "evidence_refs": [f"source:function {function['name']}", f"source:auth_class {_auth_class(body)}"],
    }


def _custom_guards(source: str) -> list[dict[str, Any]]:
    guards: list[dict[str, Any]] = []
    for match in re.finditer(r"\bmodifier\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:\([^)]*\))?\s*\{", source):
        name = match.group(1)
        body = _body_at(source, match.end() - 1)
        actor = _actor_variable(body)
        if not actor:
            continue
        guards.append(
            {
                "name": name,
                "actor_variable": actor,
                "semantic_role": _role_for_variable(actor),
                "evidence_refs": [f"source:modifier {name}", f"source:actor variable {actor}"],
            }
        )
    return guards


def _critical_writes(body: str) -> list[str]:
    writes: set[str] = set()
    for match in re.finditer(r"\b(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*[^=]", body):
        name = match.group("name")
        if _is_critical_identifier(name):
            writes.add(name)
    for match in re.finditer(r"\b(?P<obj>[A-Za-z_][A-Za-z0-9_]*)\s*\.\s*(?:value|addr|account)\s*=\s*[^=]", body):
        name = match.group("obj")
        if _is_critical_identifier(name):
            writes.add(name)
    for match in re.finditer(r"\b_(?:setupRole|grantRole)\s*\(\s*(?P<role>[A-Za-z_][A-Za-z0-9_]*)", body):
        writes.add(f"role:{match.group('role')}")
    return sorted(writes)


def _best_reader_for_writes(entry: dict[str, Any], writes: list[str]) -> str:
    readers = {str(item.get("name") or "") for item in entry.get("readers") or []}
    if any(item.startswith("role:") for item in writes) and "hasRole" in readers:
        return "hasRole(bytes32,address)"
    for write in writes:
        if write.startswith("role:"):
            continue
        stripped = write.lstrip("_")
        candidates = [
            stripped,
            f"get{stripped[:1].upper()}{stripped[1:]}",
            f"{stripped}Address",
            "owner" if "owner" in stripped.lower() else "",
            "admin" if "admin" in stripped.lower() else "",
        ]
        for candidate in candidates:
            if candidate and candidate in readers:
                return f"{candidate}()"
    for fallback in ("owner", "admin", "guardian", "controller"):
        if fallback in readers:
            return f"{fallback}()"
    return ""


def _implementation_reader(entry: dict[str, Any], dossier: dict[str, Any]) -> str:
    readers = {str(item.get("name") or "") for item in entry.get("readers") or []}
    if "implementation" in readers:
        return "implementation()"
    if dossier.get("proxy_context"):
        return "EIP1967_IMPLEMENTATION_SLOT"
    return ""


def _validate_one(entry: dict[str, Any] | None, proposal: dict[str, Any]) -> dict[str, Any]:
    if not entry:
        return _validation_result("rejected", "source_relation_missing", proposal)
    kind = str(proposal.get("proposal_kind") or "")
    target = str(proposal.get("target_symbol") or "")
    if kind == "initializer_semantic_mapping":
        valid = _initializer_exists(entry, target) and bool((proposal.get("semantic_payload") or {}).get("critical_writes")) and bool(
            (proposal.get("semantic_payload") or {}).get("measurable_reader")
        )
        return _validation_result("accepted" if valid else "rejected", "source_backed" if valid else "initializer_evidence_missing", proposal)
    if kind == "uups_authorize_upgrade_mapping":
        valid = _function_exists(entry, target) and bool((proposal.get("semantic_payload") or {}).get("measurable_reader"))
        return _validation_result("accepted" if valid else "rejected", "authorize_upgrade_evidence_missing", proposal)
    if kind == "custom_guard_semantic_mapping":
        valid = any(str(item.get("name") or "") == target for item in entry.get("custom_guards") or [])
        return _validation_result("accepted" if valid else "rejected", "custom_guard_source_missing", proposal)
    return _validation_result("rejected", "unknown_proposal_kind", proposal)


def _validation_result(status: str, reason: str, proposal: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": status,
        "reason": reason,
        "proposal_id": proposal.get("proposal_id"),
        "proposal_kind": proposal.get("proposal_kind"),
        "proposal": proposal,
    }


def _proposal(kind: str, relation: str, target_symbol: str, payload: dict[str, Any], refs: list[str]) -> dict[str, Any]:
    seed = f"{kind}|{relation}|{target_symbol}|{payload}|{refs}"
    return {
        "proposal_id": f"PUP-{short_hash(seed)}",
        "proposal_kind": kind,
        "source_relation": relation,
        "target_symbol": target_symbol,
        "semantic_payload": payload,
        "evidence_refs": sorted(set(str(item) for item in refs if item)),
        "status": "candidate",
    }


def _is_initializer(function: dict[str, Any]) -> bool:
    name = str(function.get("name") or "").lower()
    header = f" {function.get('header') or ''} "
    return name.startswith("initialize") or " initializer" in header or " reinitializer" in header


def _is_critical_identifier(value: str) -> bool:
    lowered = value.lower()
    return any(marker in lowered for marker in CRITICAL_ROLE_MARKERS)


def _auth_class(value: str) -> str:
    compact = re.sub(r"\s+", "", value)
    protected_markers = ("onlyOwner", "onlyRole", "hasRole", "_checkOwner", "DEFAULT_ADMIN_ROLE")
    if any(marker in value or marker in compact for marker in protected_markers):
        return "protected"
    if "revert(" in compact and "if(" not in compact and "require(" not in compact:
        return "revert_only"
    return "weak_or_ambiguous"


def _actor_variable(body: str) -> str:
    compact = re.sub(r"\s+", "", body)
    patterns = [
        r"msg\.sender==(?P<name>[A-Za-z_][A-Za-z0-9_]*)",
        r"_msgSender\(\)==(?P<name>[A-Za-z_][A-Za-z0-9_]*)",
        r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)==msg\.sender",
    ]
    for pattern in patterns:
        match = re.search(pattern, compact)
        if match and _is_critical_identifier(match.group("name")):
            return match.group("name")
    return ""


def _role_for_variable(value: str) -> str:
    lowered = value.lower()
    if "proxy" in lowered and "admin" in lowered:
        return "proxy_admin"
    if "owner" in lowered:
        return "owner"
    if "guardian" in lowered:
        return "guardian"
    if "govern" in lowered:
        return "governance"
    if "admin" in lowered:
        return "admin"
    return "custom_authorized_actor"


def _visibility(header: str) -> str:
    match = re.search(r"\b(public|external|internal|private)\b", header)
    return match.group(1) if match else "unknown"


def _body_at(source: str, start: int) -> str:
    depth = 0
    for index in range(start, len(source)):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start + 1 : index]
    return ""


def _source_text(source_manifest: dict[str, Any]) -> str:
    return "\n".join(str(value) for value in (source_manifest.get("source_files") or {}).values())


def _implementation_manifest(source_manifest: dict[str, Any]) -> dict[str, Any]:
    related = source_manifest.get("related_sources")
    if isinstance(related, dict):
        implementation = related.get("implementation")
        if isinstance(implementation, dict) and implementation.get("status") == "resolved":
            return implementation
    return {}


def _function_exists(entry: dict[str, Any], name: str) -> bool:
    return any(str(item.get("name") or "") == name for item in entry.get("functions") or [])


def _initializer_exists(entry: dict[str, Any], name: str) -> bool:
    return any(str(item.get("name") or "") == name for item in entry.get("initializers") or [])


def _codable_args(inputs: list[dict[str, Any]]) -> list[str]:
    args = []
    for item in inputs:
        arg_type = str(item.get("type") or "")
        if arg_type == "address":
            args.append("address(this)")
        elif arg_type.startswith("uint"):
            args.append("1")
        elif arg_type == "bool":
            args.append("true")
        elif arg_type == "string":
            args.append('"vassago"')
    return args


def _unsupported_args(inputs: list[dict[str, Any]]) -> list[str]:
    unsupported = []
    for item in inputs:
        arg_type = str(item.get("type") or "")
        if arg_type == "address" or arg_type.startswith("uint") or arg_type in {"bool", "string"}:
            continue
        unsupported.append(arg_type or "unknown")
    return unsupported
