"""Source-backed SC01 recognizers.

These helpers are deliberately narrow. They recognize concrete source evidence
needed by bootstrap fixtures and early real-contract triage, but they do not
read chain state or claim live impact.
"""

from __future__ import annotations

import re
from typing import Any


ADMIN_VARIABLES = ("owner", "admin", "governor")


def evaluate_uninitialized_uups_initializer(source_manifest: dict[str, Any]) -> dict[str, Any]:
    """Return source-backed evidence for the UUPS uninitialized initializer thesis."""

    source_text = _source_text(source_manifest)
    abi = list(source_manifest.get("abi") or [])
    contract_name = _contract_name(source_manifest, source_text)
    init_abi = _abi_function(abi, "initialize")
    upgrade_abi = _abi_function(abi, "upgradeTo") or _abi_function(abi, "upgradeToAndCall")
    initializer = _function_body(source_text, "initialize")
    upgrade = _function_body(source_text, "upgradeTo") or _function_body(source_text, "upgradeToAndCall")
    owner_write = _owner_write(initializer.get("body", ""))
    reader = _reader_for(source_text, abi, owner_write.get("variable"))
    blockers = []

    if "pragma solidity" not in source_text:
        blockers.append("source_not_compile_context")
    if not initializer:
        blockers.append("initialize_function_missing")
    if initializer and initializer.get("visibility") not in {"external", "public"}:
        blockers.append("initialize_not_external_or_public")
    if "_disableInitializers" in source_text:
        blockers.append("disable_initializers_present")
    if not owner_write:
        blockers.append("initializer_admin_write_missing")
    if not reader:
        blockers.append("admin_reader_missing")
    if not upgrade_abi and "function upgradeTo" not in source_text and "function upgradeToAndCall" not in source_text:
        blockers.append("upgrade_function_missing")
    if not upgrade:
        blockers.append("upgrade_body_missing")
    if "_authorizeUpgrade" not in source_text:
        blockers.append("authorize_upgrade_missing")

    init_inputs = list((init_abi or {}).get("inputs") or [])
    codable_args = _codable_initializer_args(init_inputs, owner_write)
    if codable_args is None:
        blockers.append("initializer_args_not_codable")

    verified = not blockers
    return {
        "verified": verified,
        "blockers": blockers,
        "contract_name": contract_name,
        "initializer_signature": _signature(init_abi, "initialize"),
        "upgrade_signature": _signature(upgrade_abi, "upgradeTo"),
        "admin_variable": owner_write.get("variable"),
        "admin_reader": reader,
        "codable_args": codable_args or [],
        "measurable_delta": _measurable_delta(owner_write.get("variable")),
        "explicit_predicate": _predicate(reader),
        "evidence_refs": _evidence_refs(verified, owner_write, reader),
    }


def evaluate_access_control_initializer(source_manifest: dict[str, Any]) -> dict[str, Any]:
    """Return source-backed evidence for an uninitialized AccessControl setup.

    This covers upgradeable contracts that seed `DEFAULT_ADMIN_ROLE` or an
    execution role inside an external/public initializer. It is intentionally
    scoped to local reproduction of the authorization takeover; live impact is
    a later state/proxy question.
    """

    source_text = _source_text(source_manifest)
    abi = list(source_manifest.get("abi") or [])
    contract_name = _contract_name(source_manifest, source_text)
    initializer = _function_body(source_text, "initialize")
    init_abi = _abi_function(abi, "initialize")
    body = initializer.get("body", "")
    header = initializer.get("header", "")
    blockers = []

    default_admin_arg = _role_setup_argument(body, "DEFAULT_ADMIN_ROLE")
    role_setups = _role_setup_calls(body)
    has_role_reader = _abi_function(abi, "hasRole") is not None
    default_role_reader = _abi_function(abi, "DEFAULT_ADMIN_ROLE") is not None or "DEFAULT_ADMIN_ROLE" in source_text

    if "pragma solidity" not in source_text:
        blockers.append("source_not_compile_context")
    if not initializer:
        blockers.append("initialize_function_missing")
    if initializer and initializer.get("visibility") not in {"external", "public"}:
        blockers.append("initialize_not_external_or_public")
    if "initializer" not in header and "initializer" not in body:
        blockers.append("initializer_modifier_missing")
    if "_disableInitializers" in source_text:
        blockers.append("disable_initializers_present")
    if not default_admin_arg:
        blockers.append("default_admin_setup_missing")
    if not has_role_reader:
        blockers.append("hasRole_reader_missing")
    if not default_role_reader:
        blockers.append("default_admin_role_reader_missing")

    init_inputs = list((init_abi or {}).get("inputs") or [])
    codable = _codable_access_control_initializer_args(init_inputs, default_admin_arg, body)
    if codable is None:
        blockers.append("initializer_args_not_codable")

    verified = not blockers
    return {
        "verified": verified,
        "blockers": blockers,
        "contract_name": contract_name,
        "initializer_signature": _signature(init_abi, "initialize"),
        "admin_variable": "_roles[DEFAULT_ADMIN_ROLE]",
        "admin_reader": "hasRole(DEFAULT_ADMIN_ROLE,address)",
        "codable_args": list((codable or {}).get("args") or []),
        "harness_setup": list((codable or {}).get("setup") or []),
        "role_setups": role_setups,
        "measurable_delta": "hasRole(DEFAULT_ADMIN_ROLE, unauthorized caller) changes false to true",
        "explicit_predicate": (
            "After an unauthorized caller invokes initialize(), "
            "hasRole(DEFAULT_ADMIN_ROLE, caller) is true."
        ),
        "evidence_refs": _access_control_evidence_refs(verified, role_setups),
    }


def evaluate_proxy_storage_collision_reinitializer(source_manifest: dict[str, Any]) -> dict[str, Any]:
    """Return partial evidence for an Audius-style proxy collision thesis."""

    source_text = _source_text(source_manifest)
    abi = list(source_manifest.get("abi") or [])
    proxy_context = dict(source_manifest.get("proxy_context") or {})
    blockers = []
    proxy_admin = _proxy_admin_storage_declaration(source_text)
    delegates = "delegatecall" in source_text and ("function ()" in source_text or "fallback" in source_text or "_fallback" in source_text)
    implementation = str(proxy_context.get("implementation") or "")
    is_proxy = str(proxy_context.get("proxy") or "").lower() in {"1", "true", "yes"}
    admin_reader = _abi_function(abi, "getAudiusProxyAdminAddress") or _abi_function(abi, "admin")
    implementation_reader = _abi_function(abi, "implementation")
    implementation_manifest = _related_implementation_manifest(source_manifest)
    implementation_source = _source_text(implementation_manifest) if implementation_manifest else ""
    implementation_contract_name = _contract_name(implementation_manifest, implementation_source) if implementation_manifest else ""
    implementation_contract_source = _contract_source_by_name(
        implementation_source,
        implementation_contract_name,
    )
    implementation_initializable = _has_initializable_slot_zero_flags(implementation_source)
    implementation_initializers = _implementation_initializer_names(implementation_contract_source or implementation_source)
    privileged_writes = _implementation_initializer_privileged_writes(
        implementation_contract_source or implementation_source,
        list((implementation_manifest or {}).get("abi") or []),
    )

    if "pragma solidity" not in source_text:
        blockers.append("source_not_compile_context")
    if not proxy_admin:
        blockers.append("slot_zero_proxy_admin_missing")
    if not delegates:
        blockers.append("delegatecall_fallback_missing")
    if not is_proxy:
        blockers.append("explorer_proxy_context_missing")
    if not implementation or implementation == "0x0000000000000000000000000000000000000000":
        blockers.append("implementation_address_missing")
    if not admin_reader:
        blockers.append("proxy_admin_reader_missing")
    if not implementation_reader:
        blockers.append("implementation_reader_missing")

    verified_proxy_side = not blockers
    missing = []
    if not implementation_source:
        missing.append("implementation_source_required")
    if not implementation_initializable:
        missing.append("implementation_initializable_slot0_layout_required")
    if not implementation_initializers:
        missing.append("implementation_initializer_required")
    if not privileged_writes:
        missing.append("initializer_privileged_write_required")
    missing.extend(
        [
            "proxy_delegatecall_initializer_calldata_required",
            "measurable_proxy_state_delta_required",
        ]
    )
    return {
        "verified": False,
        "proxy_side_verified": verified_proxy_side,
        "blockers": blockers,
        "missing_proof_pieces": missing,
        "contract_name": _contract_name(source_manifest, source_text),
        "implementation_address": implementation,
        "proxy_admin_variable": proxy_admin.get("variable"),
        "proxy_admin_reader": _signature(admin_reader, "getAudiusProxyAdminAddress"),
        "implementation_reader": _signature(implementation_reader, "implementation"),
        "implementation_source_status": "resolved" if implementation_source else "missing",
        "implementation_contract_name": implementation_contract_name,
        "implementation_initializable": implementation_initializable,
        "implementation_initializers": implementation_initializers,
        "initializer_privileged_writes": privileged_writes,
        "measurable_delta": "initializer changes privileged proxy/governance state through delegatecall",
        "explicit_predicate": (
            "Proxy fallback delegatecalls implementation initializer and bypasses "
            "Initializable guard because proxy slot-zero admin collides with implementation flags."
        ),
        "evidence_refs": _proxy_collision_evidence_refs(verified_proxy_side, proxy_admin, privileged_writes),
    }


def evaluate_public_normal_behavior(source_manifest: dict[str, Any], matched_functions: list[str]) -> dict[str, Any]:
    """Classify source-backed safe public behavior that should not become SC01 proof."""

    source_text = _source_text(source_manifest)
    bodies = [_function_body(source_text, str(name).split("(")[0]) for name in matched_functions]
    bodies = [body for body in bodies if body]
    if not bodies:
        return {"rejected": False, "blockers": ["matched_function_body_missing"]}
    classifications = []
    refs = []
    for body in bodies:
        content = body.get("body", "")
        if _writes_admin_variable(content):
            return {"rejected": False, "blockers": ["admin_variable_write_present"]}
        if _has_dangerous_external_sink(content):
            return {"rejected": False, "blockers": ["external_sink_present"]}
        if _is_user_funded_accounting(content):
            classifications.append("caller_funded_accounting")
            refs.extend(["source:msg.value", "source:caller-indexed accounting"])
        elif _is_protocol_lock_accounting(content):
            classifications.append("protocol_lock_accounting")
            refs.extend(["source:onlyWhenUnlocked", "source:protocol delta accounting"])
        elif _is_caller_scoped_operator(content):
            classifications.append("caller_scoped_operator")
            refs.extend(["source:msg.sender scoped operator mapping", "source:OperatorSet"])
        elif _is_public_lifecycle(content):
            classifications.append("public_lifecycle")
            refs.extend(["source:lifecycle condition", "source:lifecycle state write"])
    if not classifications:
        return {"rejected": False, "blockers": ["no_public_normal_behavior_policy_matched"]}
    return {
        "rejected": True,
        "classification": sorted(set(classifications))[0],
        "reason": "Source shows public protocol/accounting behavior without admin-state write.",
        "evidence_refs": sorted(set(refs)),
    }


def should_use_uups_initializer_harness(source_manifest: dict[str, Any]) -> bool:
    return bool(evaluate_uninitialized_uups_initializer(source_manifest).get("verified"))


def should_use_access_control_initializer_harness(source_manifest: dict[str, Any]) -> bool:
    return bool(evaluate_access_control_initializer(source_manifest).get("verified"))


def evaluate_known_non_sc01_pattern(
    source_manifest: dict[str, Any],
    thesis_id: str,
    matched_functions: list[str],
) -> dict[str, Any]:
    """Reject common protocol/proxy patterns that are not SC01 gaps by themselves."""

    source_text = _source_text(source_manifest)
    if not matched_functions:
        return {
            "rejected": True,
            "classification": "no_function_level_evidence",
            "reason": "Corpus motif matched global source text but no concrete function-level evidence.",
            "evidence_refs": ["source-truth:no matched function"],
        }
    if thesis_id == "uups_weak_auth" and _is_transparent_proxy_admin_path(source_text, matched_functions):
        return {
            "rejected": True,
            "classification": "transparent_proxy_admin_path",
            "reason": "Upgrade functions are gated by proxy admin context, not an unguarded UUPS authorize path.",
            "evidence_refs": ["source:ifAdmin", "source:_admin", "source:_setImplementation"],
        }
    if thesis_id == "uups_weak_auth" and _is_custom_proxy_admin_upgrade_path(source_text, matched_functions):
        return {
            "rejected": True,
            "classification": "custom_proxy_admin_path",
            "reason": "upgradeTo is guarded by custom proxyAdmin storage and is not a UUPS _authorizeUpgrade path.",
            "evidence_refs": ["source:proxyAdmin", "source:require msg.sender == proxyAdmin", "source:_upgradeTo"],
        }
    if thesis_id == "role_admin_escalation" and _is_token_approval_operator(matched_functions):
        return {
            "rejected": True,
            "classification": "token_approval_operator",
            "reason": "Matched functions are token approval/operator APIs scoped to token owner, not contract role-admin mutation.",
            "evidence_refs": ["abi:approval/operator standard"],
        }
    if thesis_id == "uninitialized_implementation_proxy" and _is_initialized_eip1967_proxy(
        source_manifest,
        source_text,
        matched_functions,
    ):
        return {
            "rejected": True,
            "classification": "initialized_eip1967_proxy",
            "reason": "Initializer is guarded by empty implementation slot and explorer context already reports a live implementation.",
            "evidence_refs": [
                "source:require _implementation() == address(0)",
                "source:IMPLEMENTATION_SLOT",
                "explorer:proxy implementation",
            ],
        }
    if thesis_id == "uninitialized_implementation_proxy" and _is_public_factory_or_pool_creation(source_text, matched_functions):
        return {
            "rejected": True,
            "classification": "public_factory_or_pool_creation",
            "reason": "Matched initializer-like function creates/configures user-requested protocol resources, not proxy admin ownership.",
            "evidence_refs": ["source:create2 or pool initializer", "source:no admin write"],
        }
    if thesis_id == "uninitialized_implementation_proxy" and _is_protocol_pool_initializer(source_text, matched_functions):
        return {
            "rejected": True,
            "classification": "protocol_pool_initializer",
            "reason": "initialize configures a protocol pool and does not assign owner/admin/governor authority.",
            "evidence_refs": ["source:PoolKey", "source:Initialize event", "source:no admin write"],
        }
    return {"rejected": False, "blockers": ["no_known_non_sc01_pattern_matched"]}


def render_initializer_call(source_manifest: dict[str, Any]) -> str:
    evaluation = evaluate_uninitialized_uups_initializer(source_manifest)
    args = list(evaluation.get("codable_args") or [])
    if not args:
        return "target.initialize();"
    return f"target.initialize({', '.join(args)});"


def render_access_control_initializer_setup(source_manifest: dict[str, Any]) -> list[str]:
    return list(evaluate_access_control_initializer(source_manifest).get("harness_setup") or [])


def render_access_control_initializer_call(source_manifest: dict[str, Any]) -> str:
    evaluation = evaluate_access_control_initializer(source_manifest)
    args = list(evaluation.get("codable_args") or [])
    if not args:
        return "target.initialize();"
    return f"target.initialize({', '.join(args)});"


def contract_name_for_source(source_manifest: dict[str, Any]) -> str:
    return _contract_name(source_manifest, _source_text(source_manifest))


def contract_name_for_harness(source_manifest: dict[str, Any]) -> str:
    evaluation = evaluate_uninitialized_uups_initializer(source_manifest)
    return str(evaluation.get("contract_name") or "FixtureUUPSPositive")


def _writes_admin_variable(body: str) -> bool:
    for variable in ADMIN_VARIABLES:
        if re.search(rf"\b{variable}\s*(?:=|\+=|-=|\*=|/=)", body):
            return True
    return False


def _has_dangerous_external_sink(body: str) -> bool:
    lowered = body.lower()
    return any(marker in lowered for marker in (".delegatecall(", ".call(", "selfdestruct", "upgradeTo("))


def _is_user_funded_accounting(body: str) -> bool:
    lowered = body.lower()
    if "msg.value" not in lowered and "msg.sender" not in lowered:
        return False
    accounting_markers = ("balance", "deposit", "share", "amount", "total")
    has_accounting_write = bool(re.search(r"\]\s*(?:\+=|-=|=)", body) or re.search(r"\b\w+\s*(?:\+=|-=|=)", body))
    return has_accounting_write and any(marker in lowered for marker in accounting_markers)


def _is_public_lifecycle(body: str) -> bool:
    lowered = body.lower()
    has_public_condition = any(marker in lowered for marker in ("block.timestamp", "block.number", "require(", "revert "))
    has_lifecycle_marker = any(marker in lowered for marker in ("status", "state", "round", "epoch", "day", "settle", "expire"))
    has_write = bool(re.search(r"\b\w+\s*(?:=|\+=|-=)", body))
    return has_public_condition and has_lifecycle_marker and has_write


def _is_protocol_lock_accounting(body: str) -> bool:
    lowered = body.lower()
    if "onlywhenunlocked" not in lowered and "nonzerodeltacount" not in lowered and "_accountdelta" not in lowered:
        return False
    return any(marker in lowered for marker in ("settle", "_settle", "currency", "delta", "msg.sender"))


def _is_caller_scoped_operator(body: str) -> bool:
    lowered = body.lower()
    return (
        "operator" in lowered
        and "msg.sender" in lowered
        and ("isoperator[msg.sender]" in lowered or "allowance[msg.sender]" in lowered)
    )


def _is_transparent_proxy_admin_path(source_text: str, matched_functions: list[str]) -> bool:
    names = {str(item).split("(")[0] for item in matched_functions}
    if not names.intersection({"upgradeTo", "upgradeToAndCall"}):
        return False
    if "_authorizeUpgrade" in source_text or "onlyProxy" in source_text:
        return False
    bodies = [_function_body(source_text, name).get("body", "") for name in names]
    headers = [_function_body(source_text, name).get("header", "") for name in names]
    joined = "\n".join(headers + bodies)
    has_admin_reader = "_admin()" in source_text or "_admin" in source_text or "function admin()" in source_text
    return "ifAdmin" in joined and "_upgradeTo" in joined and "_setImplementation" in source_text and has_admin_reader


def _is_custom_proxy_admin_upgrade_path(source_text: str, matched_functions: list[str]) -> bool:
    names = {str(item).split("(")[0] for item in matched_functions}
    if "upgradeTo" not in names:
        return False
    if "_authorizeUpgrade" in source_text or "onlyProxy" in source_text:
        return False
    body = _function_body(source_text, "upgradeTo").get("body", "")
    compact = re.sub(r"\s+", "", body)
    return (
        "proxyAdmin" in source_text
        and "_upgradeTo" in body
        and "msg.sender==proxyAdmin" in compact
        and "functionimplementation()" in re.sub(r"\s+", "", source_text)
    )


def _is_token_approval_operator(matched_functions: list[str]) -> bool:
    names = {str(item).split("(")[0] for item in matched_functions}
    token_approval_names = {
        "allowance",
        "approve",
        "getApproved",
        "isApprovedForAll",
        "positions",
        "setApprovalForAll",
        "setOperator",
    }
    return bool(names) and names.issubset(token_approval_names)


def _is_initialized_eip1967_proxy(
    source_manifest: dict[str, Any],
    source_text: str,
    matched_functions: list[str],
) -> bool:
    names = {str(item).split("(")[0] for item in matched_functions}
    if "initialize" not in names:
        return False
    proxy_context = dict(source_manifest.get("proxy_context") or {})
    implementation = str(proxy_context.get("implementation") or "").lower()
    is_proxy = str(proxy_context.get("proxy") or "").lower() in {"1", "true", "yes"}
    if not is_proxy or implementation in {"", "0x", "0x0000000000000000000000000000000000000000"}:
        return False
    body = _function_body(source_text, "initialize").get("body", "")
    has_empty_impl_guard = "_implementation() == address(0)" in body or "_implementation()==address(0)" in body
    return has_empty_impl_guard and "IMPLEMENTATION_SLOT" in source_text


def _is_public_factory_or_pool_creation(source_text: str, matched_functions: list[str]) -> bool:
    names = {str(item).split("(")[0] for item in matched_functions}
    if names.intersection({"createPair", "createAndInitializePoolIfNecessary"}):
        return True
    bodies = "\n".join(_function_body(source_text, name).get("body", "") for name in names)
    if _writes_admin_variable(bodies):
        return False
    lowered = bodies.lower()
    return ("create2" in lowered and "initialize" in lowered) or "poolinitializer" in source_text.lower()


def _is_protocol_pool_initializer(source_text: str, matched_functions: list[str]) -> bool:
    names = {str(item).split("(")[0] for item in matched_functions}
    if "initialize" not in names:
        return False
    body = _function_body(source_text, "initialize")
    content = body.get("body", "")
    header = body.get("header", "")
    if not content:
        return False
    if _writes_admin_variable(content):
        return False
    has_pool_key_context = "PoolKey" in source_text or "key.currency0" in content or "key.toId" in content
    return has_pool_key_context and "emit Initialize" in content


def _source_text(source_manifest: dict[str, Any]) -> str:
    return "\n".join(str(value) for value in (source_manifest.get("source_files") or {}).values())


def _related_implementation_manifest(source_manifest: dict[str, Any]) -> dict[str, Any]:
    related = dict(source_manifest.get("related_sources") or {})
    implementation = related.get("implementation")
    if not isinstance(implementation, dict) or implementation.get("status") != "resolved":
        return {}
    return implementation


def _related_implementation_source(source_manifest: dict[str, Any]) -> str:
    implementation = _related_implementation_manifest(source_manifest)
    return _source_text(implementation) if implementation else ""


def _has_initializable_slot_zero_flags(source_text: str) -> bool:
    if not source_text:
        return False
    compact = re.sub(r"\s+", " ", source_text)
    has_flags = (
        re.search(r"\bbool\s+(?:private|internal|public)?\s*initialized\s*;", compact) is not None
        and re.search(r"\bbool\s+(?:private|internal|public)?\s*initializing\s*;", compact) is not None
    )
    has_initializer_modifier = "modifier initializer()" in source_text and "initialized" in source_text and "initializing" in source_text
    return has_flags or has_initializer_modifier


def _implementation_initializer_names(source_text: str) -> list[str]:
    if not source_text:
        return []
    names = []
    for match in re.finditer(r"\bfunction\s+([A-Za-z_][A-Za-z0-9_]*)\s*\([^)]*\)(?P<header>[^{;]*)\{", source_text):
        name = match.group(1)
        header = match.group("header")
        if name.lower().startswith("initialize") or " initializer" in f" {header} ":
            names.append(name)
    return sorted(set(names))


def _implementation_initializer_privileged_writes(source_text: str, abi: list[dict[str, Any]]) -> list[dict[str, str]]:
    initializer = _function_body(source_text, "initialize")
    body = initializer.get("body", "")
    if not body:
        return []
    writes = []
    for match in re.finditer(
        r"\b(?P<variable>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?P<value>[A-Za-z_][A-Za-z0-9_]*\([^;\n]*\)|_[A-Za-z_][A-Za-z0-9_]*|[A-Za-z_][A-Za-z0-9_]*)\s*;",
        body,
    ):
        variable = match.group("variable")
        reader = _reader_for_variable(source_text, abi, variable)
        if not reader:
            continue
        if not _is_privileged_initializer_variable(variable):
            continue
        writes.append(
            {
                "variable": variable,
                "value": match.group("value"),
                "reader": reader,
                "initializer": "initialize",
            }
        )
    return writes


def _reader_for_variable(source_text: str, abi: list[dict[str, Any]], variable: str) -> str:
    direct = _abi_function(abi, variable)
    if direct:
        return _signature(direct, variable)
    camel = variable[:1].upper() + variable[1:]
    for candidate in (f"get{camel}", f"is{camel}", f"{variable}Address"):
        function = _abi_function(abi, candidate)
        if function:
            return _signature(function, candidate)
    for match in re.finditer(r"\bfunction\s+([A-Za-z_][A-Za-z0-9_]*)\s*\([^)]*\)(?P<header>[^{;]*)\{", source_text):
        name = match.group(1)
        start = match.end() - 1
        body = _body_from_index(source_text, start)
        if re.search(rf"\breturn\s+(?:address\()?{re.escape(variable)}\)?\s*;", body):
            return f"{name}()"
    return ""


def _is_privileged_initializer_variable(variable: str) -> bool:
    lowered = variable.lower()
    markers = (
        "admin",
        "guardian",
        "govern",
        "registry",
        "voting",
        "quorum",
        "execution",
        "inprogress",
        "staking",
        "delegate",
        "serviceprovider",
    )
    return any(marker in lowered for marker in markers)


def _proxy_admin_storage_declaration(source_text: str) -> dict[str, str]:
    match = re.search(r"\baddress\s+(?:private|public|internal)?\s*(?P<name>proxyAdmin)\s*;", source_text)
    if match:
        return {"variable": match.group("name"), "type": "address", "slot_assumption": "slot0_first_proxy_state"}
    return {}


def _proxy_collision_evidence_refs(
    verified_proxy_side: bool,
    proxy_admin: dict[str, str],
    privileged_writes: list[dict[str, str]] | None = None,
) -> list[str]:
    refs = ["source:delegatecall fallback", "source:EIP1967 implementation slot"]
    if proxy_admin:
        refs.append(f"source:proxy admin storage {proxy_admin['variable']}")
    for write in privileged_writes or []:
        refs.append(f"implementation:initializer write {write.get('variable')}")
        refs.append(f"implementation:reader {write.get('reader')}")
    if verified_proxy_side:
        refs.append("explorer:proxy implementation")
    return sorted(set(refs))


def _contract_name(source_manifest: dict[str, Any], source_text: str) -> str:
    metadata = dict(source_manifest.get("metadata") or {})
    if metadata.get("contract_name"):
        return str(metadata["contract_name"])
    match = re.search(r"\bcontract\s+([A-Za-z_][A-Za-z0-9_]*)\b", source_text)
    return match.group(1) if match else "Target"


def _abi_function(abi: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    for item in abi:
        if item.get("type") == "function" and item.get("name") == name:
            return item
    return None


def _signature(item: dict[str, Any] | None, fallback_name: str) -> str:
    if not item:
        return fallback_name
    inputs = ",".join(str(arg.get("type") or "") for arg in item.get("inputs") or [])
    return f"{item.get('name') or fallback_name}({inputs})"


def _function_body(source_text: str, name: str) -> dict[str, str]:
    match = re.search(rf"\bfunction\s+{re.escape(name)}\s*\([^)]*\)(?P<header>[^\{{;]*)\{{", source_text)
    if not match:
        return {}
    start = match.end() - 1
    depth = 0
    for index in range(start, len(source_text)):
        char = source_text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                header = match.group("header")
                return {
                    "header": header,
                    "body": source_text[start + 1 : index],
                    "visibility": _visibility(header),
                }
    return {}


def _body_from_index(source_text: str, start: int) -> str:
    depth = 0
    for index in range(start, len(source_text)):
        char = source_text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source_text[start + 1 : index]
    return ""


def _contract_source_by_name(source_text: str, name: str) -> str:
    if not source_text or not name:
        return ""
    match = re.search(rf"\bcontract\s+{re.escape(name)}\b[^\{{]*\{{", source_text)
    if not match:
        return ""
    start = match.end() - 1
    body = _body_from_index(source_text, start)
    return source_text[match.start() : start + len(body) + 2]


def _visibility(header: str) -> str:
    for value in ("external", "public", "internal", "private"):
        if re.search(rf"\b{value}\b", header):
            return value
    return "unknown"


def _owner_write(body: str) -> dict[str, str]:
    for variable in ADMIN_VARIABLES:
        match = re.search(
            rf"\b{variable}\s*=\s*(?P<value>msg\.sender|_msgSender\(\)|[A-Za-z_][A-Za-z0-9_]*)\b",
            body,
        )
        if match:
            return {"variable": variable, "value": match.group("value")}
    return {}


def _reader_for(source_text: str, abi: list[dict[str, Any]], variable: str | None) -> str:
    if not variable:
        return ""
    for item in abi:
        if item.get("type") != "function" or item.get("name") != variable:
            continue
        if item.get("stateMutability") in {"view", "pure"} and not item.get("inputs"):
            return f"{variable}()"
    if re.search(rf"\baddress\s+public\s+{re.escape(variable)}\b", source_text):
        return f"{variable}()"
    return ""


def _codable_initializer_args(inputs: list[dict[str, Any]], owner_write: dict[str, str]) -> list[str] | None:
    if not inputs:
        return []
    if len(inputs) == 1 and inputs[0].get("type") == "address":
        value = owner_write.get("value")
        if value and value not in {"msg.sender", "_msgSender()"}:
            return ["address(this)"]
    return None


def _codable_access_control_initializer_args(
    inputs: list[dict[str, Any]],
    default_admin_arg: str,
    body: str,
) -> dict[str, list[str]] | None:
    if not inputs:
        return {"setup": [], "args": []}
    setup: list[str] = []
    args: list[str] = []
    for index, item in enumerate(inputs):
        arg_type = str(item.get("type") or "")
        arg_name = str(item.get("name") or f"arg{index}")
        if arg_type == "address":
            if default_admin_arg and default_admin_arg == arg_name:
                args.append("address(this)")
            else:
                args.append("address(this)")
        elif arg_type == "address[]":
            variable = f"vassagoAccounts{index}"
            length = "1" if arg_name in body else "0"
            setup.append(f"address[] memory {variable} = new address[]({length});")
            if length == "1":
                setup.append(f"{variable}[0] = address(this);")
            args.append(variable)
        else:
            return None
    return {"setup": setup, "args": args}


def _role_setup_calls(body: str) -> list[dict[str, str]]:
    calls = []
    pattern = re.compile(
        r"\b_(?:setupRole|grantRole)\s*\(\s*(?P<role>[A-Za-z_][A-Za-z0-9_]*)\s*,\s*(?P<account>[^)]+?)\s*\)"
    )
    for match in pattern.finditer(body):
        calls.append({"role": match.group("role"), "account": match.group("account").strip()})
    return calls


def _role_setup_argument(body: str, role_name: str) -> str:
    for call in _role_setup_calls(body):
        if call.get("role") == role_name:
            return str(call.get("account") or "")
    return ""


def _access_control_evidence_refs(verified: bool, role_setups: list[dict[str, str]]) -> list[str]:
    refs = ["source:function initialize", "source:AccessControl role readers"]
    refs.extend(f"source:initializer role setup {item['role']}" for item in role_setups if item.get("role"))
    if verified:
        refs.append("source:no _disableInitializers")
    return sorted(set(refs))


def _measurable_delta(variable: str | None) -> str:
    name = variable or "admin"
    return f"{name} changes from deployment default to unauthorized caller"


def _predicate(reader: str) -> str:
    return f"After an unauthorized caller invokes initialize(), {reader or 'admin reader'} equals the caller."


def _evidence_refs(verified: bool, owner_write: dict[str, str], reader: str) -> list[str]:
    refs = ["source:function initialize", "source:function upgradeTo", "source:_authorizeUpgrade"]
    if owner_write:
        refs.append(f"source:initializer writes {owner_write['variable']}")
    if reader:
        refs.append(f"source:reader {reader}")
    if verified:
        refs.append("source:no _disableInitializers")
    return refs
