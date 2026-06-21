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


def render_initializer_call(source_manifest: dict[str, Any]) -> str:
    evaluation = evaluate_uninitialized_uups_initializer(source_manifest)
    args = list(evaluation.get("codable_args") or [])
    if not args:
        return "target.initialize();"
    return f"target.initialize({', '.join(args)});"


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


def _source_text(source_manifest: dict[str, Any]) -> str:
    return "\n".join(str(value) for value in (source_manifest.get("source_files") or {}).values())


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
