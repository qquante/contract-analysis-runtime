"""Proxy/upgrade/signature source-truth mapper.

The mapper is source-backed and thesis-scoped. It avoids using historical case
ids, contract names or addresses as rules; those belong only in post-run
scoring.
"""

from __future__ import annotations

import re
from typing import Any

from vassago_contract_runtime.sc01_proxy_semantics import accepted_semantic_proposals


RELEVANT_THESES = {
    "uninitialized_implementation_proxy",
    "uups_weak_auth",
    "role_admin_escalation",
}

PROXY_ADMIN_FUNCTIONS = {"admin", "changeAdmin", "implementation", "upgradeTo", "upgradeToAndCall"}
AUTH_MARKERS = (
    "onlyOwner",
    "onlyRole",
    "hasRole",
    "owner()",
    "_checkOwner",
    "msg.sender == owner",
    "msg.sender==owner",
    "_msgSender() == owner",
    "_msgSender()==owner",
    "DEFAULT_ADMIN_ROLE",
)
CRITICAL_MARKERS = (
    "owner",
    "admin",
    "governor",
    "guardian",
    "operator",
    "implementation",
    "registry",
    "router",
    "treasury",
    "oracle",
    "role",
)


def evaluate_proxy_upgrade_signature(
    source_manifest: dict[str, Any],
    thesis_id: str,
    matched_functions: list[str],
    *,
    semantic_validation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify proxy/upgrade candidates with source-backed evidence."""

    if not _is_relevant(thesis_id, matched_functions):
        return {"applicable": False, "status": "not_applicable"}

    target_source = _source_text(source_manifest)
    target_abi = list(source_manifest.get("abi") or [])
    implementation = _implementation_manifest(source_manifest)
    implementation_source = _source_text(implementation)
    implementation_abi = list(implementation.get("abi") or [])
    proxy_context = dict(source_manifest.get("proxy_context") or {})
    names = _function_names(matched_functions)
    proxy_like = _is_proxy_like(source_manifest, target_source)
    implementation_source_missing = proxy_like and not implementation_source

    if _is_transparent_proxy_admin_context(target_source, names):
        if thesis_id == "uups_weak_auth" or not _has_initializer_signal(names, implementation_source, implementation_abi):
            return _rejected(
                "transparent_proxy_admin_path",
                "Matched upgrade/admin functions are protected by transparent proxy admin context.",
                [
                    "source:transparent proxy admin path",
                    "source:ifAdmin/_fallback admin separation",
                    "source:EIP1967 implementation/admin slots",
                ],
            )

    if thesis_id == "uninitialized_implementation_proxy":
        if not proxy_like and not implementation_source and "proxyInitialize" not in names:
            return {"applicable": False, "status": "not_applicable"}
        return _evaluate_initializer_context(
            proxy_like=proxy_like,
            implementation_source_missing=implementation_source_missing,
            proxy_context=proxy_context,
            target_source=target_source,
            target_abi=target_abi,
            implementation_source=implementation_source,
            implementation_abi=implementation_abi,
            names=names,
            semantic_validation=semantic_validation or {},
        )

    if thesis_id == "uups_weak_auth":
        return _evaluate_uups_context(
            proxy_like=proxy_like,
            implementation_source_missing=implementation_source_missing,
            proxy_context=proxy_context,
            target_source=target_source,
            target_abi=target_abi,
            implementation_source=implementation_source,
            implementation_abi=implementation_abi,
            names=names,
            semantic_validation=semantic_validation or {},
        )

    if thesis_id == "role_admin_escalation":
        return _evaluate_role_admin_context(target_source, target_abi, implementation_source, implementation_abi, names)

    return {"applicable": False, "status": "not_applicable"}


def _evaluate_initializer_context(
    *,
    proxy_like: bool,
    implementation_source_missing: bool,
    proxy_context: dict[str, Any],
    target_source: str,
    target_abi: list[dict[str, Any]],
    implementation_source: str,
    implementation_abi: list[dict[str, Any]],
    names: set[str],
    semantic_validation: dict[str, Any],
) -> dict[str, Any]:
    source = implementation_source or target_source
    abi = implementation_abi or target_abi
    initializer_names = _initializer_function_names(source, abi)
    if not initializer_names and names.intersection(PROXY_ADMIN_FUNCTIONS):
        return _rejected(
            "proxy_admin_functions_without_initializer",
            "The candidate matched proxy admin/upgrade functions but no initializer-like implementation function.",
            ["abi:proxy admin functions", "source:no initializer-like implementation function"],
        )
    if implementation_source_missing:
        return _blocked(
            "proxy_implementation_source_missing",
            ["implementation_source_required", "initializer_source_truth_required"],
            ["explorer:proxy context", "explorer:implementation address present"],
            proxy_context=proxy_context,
        )
    initializer = _best_initializer(source, initializer_names)
    if not initializer:
        return _blocked(
            "initializer_source_missing",
            ["initializer_source_truth_required"],
            ["source:no initializer body"],
            proxy_context=proxy_context,
        )
    header = initializer.get("header", "")
    body = initializer.get("body", "")
    if not _is_public_or_external(header):
        return _rejected(
            "initializer_not_external_or_public",
            "Initializer-like function is not externally callable.",
            [f"source:{initializer['name']} visibility"],
        )
    if "_disableInitializers" in source:
        return _rejected(
            "disable_initializers_present",
            "Implementation source contains _disableInitializers(), blocking the generic uninitialized-implementation thesis.",
            ["source:_disableInitializers"],
        )
    semantic_initializer = _semantic_initializer(semantic_validation, initializer["name"])
    semantic_payload = dict(semantic_initializer.get("semantic_payload") or {}) if semantic_initializer else {}
    critical_writes = _critical_writes(body)
    if not critical_writes:
        critical_writes = list(semantic_payload.get("critical_writes") or [])
    if not critical_writes:
        return _blocked(
            "initializer_without_measurable_critical_write",
            ["initializer_privileged_write_required", "measurable_delta"],
            [f"source:{initializer['name']}"],
            proxy_context=proxy_context,
        )
    reader = _reader_for_any(source, abi, critical_writes) or str(semantic_payload.get("measurable_reader") or "")
    if not reader:
        return _blocked(
            "critical_reader_missing",
            ["measurable_reader"],
            [f"source:{initializer['name']} critical write"],
            proxy_context=proxy_context,
            critical_writes=critical_writes,
        )
    codable_args, unsupported_args = _codable_args_for_initializer(abi, initializer["name"])
    if not codable_args and semantic_payload.get("codable_args"):
        codable_args = list(semantic_payload.get("codable_args") or [])
    missing_proof_pieces = ["proxy_or_implementation_state_impact"]
    if unsupported_args:
        missing_proof_pieces.append("codable_initializer_args")
    return _verified(
        "uninitialized_proxy_or_implementation_initializer",
        runtime_runner="proxy_upgrade_signature_runtime",
        actor_model="unauthorized_external_initializer_caller",
        codable_args=codable_args,
        measurable_reader=reader,
        measurable_delta=f"{reader} changes after unauthorized initializer call",
        explicit_predicate=f"Unauthorized caller invokes {initializer['name']}(...) and changes {reader}.",
        missing_proof_pieces=missing_proof_pieces,
        evidence_refs=[
            f"source:{initializer['name']} external/public initializer",
            f"source:critical writes {', '.join(critical_writes)}",
            f"source:reader {reader}",
            *(list(semantic_initializer.get("evidence_refs") or []) if semantic_initializer else []),
            *[f"abi:unsupported initializer arg {arg}" for arg in unsupported_args],
        ],
        proxy_context=proxy_context,
        critical_writes=critical_writes,
    )


def _evaluate_uups_context(
    *,
    proxy_like: bool,
    implementation_source_missing: bool,
    proxy_context: dict[str, Any],
    target_source: str,
    target_abi: list[dict[str, Any]],
    implementation_source: str,
    implementation_abi: list[dict[str, Any]],
    names: set[str],
    semantic_validation: dict[str, Any],
) -> dict[str, Any]:
    source = implementation_source or target_source
    abi = implementation_abi or target_abi
    if implementation_source_missing:
        return _blocked(
            "proxy_implementation_source_missing",
            ["implementation_source_required", "authorize_upgrade_source_required"],
            ["explorer:proxy context", "explorer:implementation address present"],
            proxy_context=proxy_context,
        )
    upgrade_names = _upgrade_function_names(source, abi, names)
    if not upgrade_names:
        return _rejected(
            "upgrade_function_missing",
            "No upgradeTo/upgradeToAndCall-style function exists in target or implementation source.",
            ["abi:no upgrade function"],
        )
    authorize = _function_body(source, "_authorizeUpgrade")
    if not authorize:
        if _has_proxy_admin_guard(source, upgrade_names):
            return _rejected(
                "proxy_admin_upgrade_guard",
                "Upgrade path is guarded by proxy/admin storage rather than UUPS _authorizeUpgrade.",
                ["source:proxy/admin guarded upgrade"],
            )
        return _blocked(
            "authorize_upgrade_missing",
            ["authorize_upgrade_source_required"],
            [f"source:{','.join(sorted(upgrade_names))}"],
            proxy_context=proxy_context,
        )
    auth_body = authorize.get("body", "")
    auth_header = authorize.get("header", "")
    if _has_auth_marker(auth_body) or _has_auth_marker(auth_header):
        return _rejected(
            "authorize_upgrade_protected",
            "_authorizeUpgrade contains owner/role authorization evidence.",
            ["source:_authorizeUpgrade authorization marker"],
        )
    if _contains_revert_only(auth_body):
        return _rejected(
            "authorize_upgrade_reverts",
            "_authorizeUpgrade always reverts or is not an executable weak-auth path.",
            ["source:_authorizeUpgrade revert"],
        )
    semantic_authorize = _semantic_authorize(semantic_validation)
    semantic_payload = dict(semantic_authorize.get("semantic_payload") or {}) if semantic_authorize else {}
    reader = _implementation_reader(source, abi, proxy_like) or str(semantic_payload.get("measurable_reader") or "")
    return _verified(
        "uups_authorize_upgrade_weak_or_ambiguous",
        runtime_runner="proxy_upgrade_signature_runtime",
        actor_model="unauthorized_external_upgrade_caller",
        codable_args=["address(newImplementation)"],
        measurable_reader=reader,
        measurable_delta=f"{reader} changes to attacker-controlled implementation",
        explicit_predicate="Unauthorized caller can pass _authorizeUpgrade and change the implementation target.",
        missing_proof_pieces=["upgrade_target_contract", "proxy_state_reader"],
        evidence_refs=[
            f"source:{','.join(sorted(upgrade_names))}",
            "source:_authorizeUpgrade without recognized authorization marker",
            f"source:reader {reader}",
            *(list(semantic_authorize.get("evidence_refs") or []) if semantic_authorize else []),
        ],
        proxy_context=proxy_context,
    )


def _evaluate_role_admin_context(
    target_source: str,
    target_abi: list[dict[str, Any]],
    implementation_source: str,
    implementation_abi: list[dict[str, Any]],
    names: set[str],
) -> dict[str, Any]:
    source = implementation_source or target_source
    abi = implementation_abi or target_abi
    role_names = {"grantRole", "revokeRole", "renounceRole", "_setRoleAdmin"}.intersection(names)
    if not role_names and "grantRole" not in source:
        return {"applicable": False, "status": "not_applicable"}
    if _has_role_admin_readers(abi) and "DEFAULT_ADMIN_ROLE" in source:
        return _blocked(
            "role_admin_graph_required",
            ["role_admin_graph", "role_reader_state", "measurable_delta"],
            ["abi:hasRole/getRoleAdmin", "source:DEFAULT_ADMIN_ROLE"],
        )
    return _blocked(
        "role_admin_reader_missing",
        ["role_admin_reader", "role_admin_graph"],
        ["source:role mutation signal"],
    )


def _is_relevant(thesis_id: str, matched_functions: list[str]) -> bool:
    names = _function_names(matched_functions)
    if thesis_id in RELEVANT_THESES:
        return True
    return bool(names.intersection(PROXY_ADMIN_FUNCTIONS | {"initialize", "grantRole", "setOwner", "setStorage"}))


def _is_proxy_like(source_manifest: dict[str, Any], source_text: str) -> bool:
    proxy_context = dict(source_manifest.get("proxy_context") or {})
    implementation = str(proxy_context.get("implementation") or "").lower()
    proxy_flag = str(proxy_context.get("proxy") or "").lower()
    return (
        proxy_flag in {"1", "true", "yes"}
        or implementation not in {"", "0x", "0x0000000000000000000000000000000000000000"}
        or "delegatecall" in source_text
        or "IMPLEMENTATION_SLOT" in source_text
    )


def _is_transparent_proxy_admin_context(source: str, names: set[str]) -> bool:
    if not names.intersection(PROXY_ADMIN_FUNCTIONS):
        return False
    compact = re.sub(r"\s+", "", source)
    return (
        "TransparentUpgradeableProxy" in source
        or "ifAdmin" in source
        or "msg.sender==_getAdmin()" in compact
        or "msg.sender==_admin()" in compact
    )


def _has_initializer_signal(names: set[str], implementation_source: str, implementation_abi: list[dict[str, Any]]) -> bool:
    return "initialize" in names or bool(_initializer_function_names(implementation_source, implementation_abi))


def _initializer_function_names(source: str, abi: list[dict[str, Any]]) -> list[str]:
    names = {
        str(item.get("name"))
        for item in abi
        if item.get("type") == "function" and str(item.get("name") or "").lower().startswith("initialize")
    }
    for match in re.finditer(r"\bfunction\s+([A-Za-z_][A-Za-z0-9_]*)\s*\([^)]*\)(?P<header>[^{;]*)\{", source):
        name = match.group(1)
        header = match.group("header")
        if name.lower().startswith("initialize") or " initializer" in f" {header} " or " reinitializer" in f" {header} ":
            names.add(name)
    return sorted(names)


def _best_initializer(source: str, names: list[str]) -> dict[str, str]:
    for name in names:
        body = _function_body(source, name)
        if body:
            body["name"] = name
            return body
    return {}


def _upgrade_function_names(source: str, abi: list[dict[str, Any]], names: set[str]) -> set[str]:
    result = {name for name in names if name in {"upgradeTo", "upgradeToAndCall"}}
    result.update(
        str(item.get("name"))
        for item in abi
        if item.get("type") == "function" and str(item.get("name") or "") in {"upgradeTo", "upgradeToAndCall"}
    )
    for name in ("upgradeTo", "upgradeToAndCall"):
        if re.search(rf"\bfunction\s+{name}\s*\(", source):
            result.add(name)
    return result


def _has_proxy_admin_guard(source: str, upgrade_names: set[str]) -> bool:
    for name in upgrade_names:
        body = _function_body(source, name)
        joined = body.get("header", "") + "\n" + body.get("body", "")
        compact = re.sub(r"\s+", "", joined)
        if "ifAdmin" in joined or "onlyProxyAdmin" in joined or "msg.sender==proxyAdmin" in compact:
            return True
    return False


def _function_body(source: str, name: str) -> dict[str, str]:
    match = re.search(rf"\bfunction\s+{re.escape(name)}\s*\([^)]*\)(?P<header>[^\{{;]*)\{{", source)
    if not match:
        return {}
    start = match.end() - 1
    depth = 0
    for index in range(start, len(source)):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return {"header": match.group("header"), "body": source[start + 1 : index]}
    return {}


def _is_public_or_external(header: str) -> bool:
    return bool(re.search(r"\b(public|external)\b", header))


def _critical_writes(body: str) -> list[str]:
    writes = []
    for match in re.finditer(r"\b(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*[^=]", body):
        name = match.group("name")
        if any(marker in name.lower() for marker in CRITICAL_MARKERS):
            writes.append(name)
    for match in re.finditer(r"\b_(?:setupRole|grantRole)\s*\(\s*(?P<role>[A-Za-z_][A-Za-z0-9_]*)", body):
        writes.append(f"role:{match.group('role')}")
    return sorted(set(writes))


def _reader_for_any(source: str, abi: list[dict[str, Any]], writes: list[str]) -> str:
    role_write = next((item for item in writes if item.startswith("role:")), "")
    if role_write and _abi_function(abi, "hasRole"):
        return "hasRole(bytes32,address)"
    for variable in writes:
        if variable.startswith("role:"):
            continue
        for candidate in _reader_candidates(variable):
            fn = _abi_function(abi, candidate)
            if fn and not fn.get("inputs"):
                return f"{candidate}()"
            if re.search(rf"\bfunction\s+{re.escape(candidate)}\s*\(\s*\)\s*(?:external|public)\s+view", source):
                return f"{candidate}()"
    if _abi_function(abi, "owner"):
        return "owner()"
    if _abi_function(abi, "admin"):
        return "admin()"
    return ""


def _reader_candidates(variable: str) -> list[str]:
    stripped = variable.lstrip("_")
    return [
        stripped,
        f"get{stripped[:1].upper()}{stripped[1:]}",
        f"{stripped}Address",
        "owner" if "owner" in stripped.lower() else "",
        "admin" if "admin" in stripped.lower() else "",
    ]


def _implementation_reader(source: str, abi: list[dict[str, Any]], proxy_like: bool) -> str:
    if _abi_function(abi, "implementation"):
        return "implementation()"
    if "IMPLEMENTATION_SLOT" in source or proxy_like:
        return "EIP1967_IMPLEMENTATION_SLOT"
    return "implementation reader"


def _has_auth_marker(value: str) -> bool:
    compact = re.sub(r"\s+", "", value)
    return any(marker in value or marker.replace(" ", "") in compact for marker in AUTH_MARKERS)


def _contains_revert_only(body: str) -> bool:
    body_without_space = re.sub(r"\s+", "", body)
    return "revert(" in body_without_space and "if(" not in body_without_space and "require(" not in body_without_space


def _has_role_admin_readers(abi: list[dict[str, Any]]) -> bool:
    return _abi_function(abi, "hasRole") is not None and _abi_function(abi, "getRoleAdmin") is not None


def _codable_args_for_initializer(abi: list[dict[str, Any]], name: str) -> tuple[list[str], list[str]]:
    fn = _abi_function(abi, name)
    if not fn:
        return [], []
    args = []
    unsupported = []
    for arg in fn.get("inputs") or []:
        arg_type = str(arg.get("type") or "")
        if arg_type == "address":
            args.append("address(this)")
        elif arg_type.startswith("uint"):
            args.append("1")
        elif arg_type == "bool":
            args.append("true")
        elif arg_type == "string":
            args.append('"vassago"')
        else:
            unsupported.append(arg_type or "unknown")
    if unsupported:
        return [], unsupported
    return args, []


def _abi_function(abi: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    for item in abi:
        if item.get("type") == "function" and item.get("name") == name:
            return item
    return None


def _function_names(functions: list[str]) -> set[str]:
    return {str(item).split("(")[0] for item in functions if item}


def _source_text(source_manifest: dict[str, Any]) -> str:
    return "\n".join(str(value) for value in (source_manifest.get("source_files") or {}).values())


def _implementation_manifest(source_manifest: dict[str, Any]) -> dict[str, Any]:
    related = source_manifest.get("related_sources")
    if not isinstance(related, dict):
        return {}
    implementation = related.get("implementation")
    if isinstance(implementation, dict) and implementation.get("status") == "resolved":
        return implementation
    return {}


def _semantic_initializer(validation: dict[str, Any], name: str) -> dict[str, Any]:
    for proposal in accepted_semantic_proposals(validation, "initializer_semantic_mapping"):
        if proposal.get("target_symbol") == name:
            return proposal
    return {}


def _semantic_authorize(validation: dict[str, Any]) -> dict[str, Any]:
    proposals = accepted_semantic_proposals(validation, "uups_authorize_upgrade_mapping")
    return proposals[0] if proposals else {}


def _verified(
    classification: str,
    *,
    runtime_runner: str,
    actor_model: str,
    codable_args: list[str],
    measurable_reader: str,
    measurable_delta: str,
    explicit_predicate: str,
    missing_proof_pieces: list[str],
    evidence_refs: list[str],
    proxy_context: dict[str, Any] | None = None,
    critical_writes: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "applicable": True,
        "status": "source_truth_verified",
        "source_truth_verified": True,
        "classification": classification,
        "runtime_runner": runtime_runner,
        "actor_model": actor_model,
        "codable_args": codable_args,
        "measurable_reader": measurable_reader,
        "measurable_delta": measurable_delta,
        "explicit_predicate": explicit_predicate,
        "missing_proof_pieces": list(missing_proof_pieces),
        "proxy_context": dict(proxy_context or {}),
        "critical_writes": list(critical_writes or []),
        "evidence_refs": sorted(set(evidence_refs)),
    }


def _blocked(
    classification: str,
    missing_proof_pieces: list[str],
    evidence_refs: list[str],
    *,
    proxy_context: dict[str, Any] | None = None,
    critical_writes: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "applicable": True,
        "status": "source_truth_blocked_proxy_upgrade_mapper",
        "source_truth_verified": False,
        "classification": classification,
        "missing_proof_pieces": list(missing_proof_pieces),
        "proxy_context": dict(proxy_context or {}),
        "critical_writes": list(critical_writes or []),
        "evidence_refs": sorted(set(evidence_refs)),
    }


def _rejected(classification: str, reason: str, evidence_refs: list[str]) -> dict[str, Any]:
    return {
        "applicable": True,
        "status": "source_truth_rejected",
        "source_truth_verified": False,
        "classification": classification,
        "reason": reason,
        "missing_proof_pieces": [],
        "evidence_refs": sorted(set(evidence_refs)),
    }
