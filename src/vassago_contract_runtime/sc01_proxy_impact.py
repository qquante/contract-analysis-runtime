"""Proxy/implementation impact review for SC01 proxy-upgrade candidates.

This module does not execute Foundry and does not make live-risk claims. It
decides whether a source-truth verified proxy initializer has enough
source/ABI/proxy evidence to move to compile-only/runtime planning.
"""

from __future__ import annotations

import re
from typing import Any


IMPACT_PIECE = "proxy_or_implementation_state_impact"


def build_proxy_upgrade_impact_review(
    source_manifest: dict[str, Any],
    source_truth: dict[str, Any],
    proposal_validation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a static impact sidecar for proxy-upgrade source-truth reviews."""

    reviews = [
        _impact_for_review(source_manifest, review, proposal_validation or {})
        for review in source_truth.get("reviews", [])
        if _is_proxy_upgrade_review(review)
    ]
    ready = [item for item in reviews if item.get("impact_ready") is True]
    return {
        "kind": "proxy_upgrade_impact_review",
        "status": "proxy_impact_ready" if ready else ("blocked" if reviews else "not_applicable"),
        "review_count": len(reviews),
        "impact_ready_count": len(ready),
        "reviews": reviews,
        "evidence_status": "static_only",
        "warning": "Impact review is a compile/runtime gate. It is not runtime evidence and makes no live exploit claim.",
    }


def proxy_impact_ready_for_review(impact_review: dict[str, Any], source_truth_id: str | None) -> dict[str, Any]:
    """Return the ready impact record for a source-truth review, if any."""

    if not source_truth_id:
        return {}
    for item in impact_review.get("reviews") or []:
        if item.get("source_truth_id") == source_truth_id and item.get("impact_ready") is True:
            return item
    return {}


def should_use_proxy_upgrade_harness(source_manifest: dict[str, Any]) -> bool:
    """Return true when the source bundle can render a generic proxy initializer harness."""

    return bool(_proxy_address(source_manifest) and _implementation_manifest(source_manifest) and _proxy_delegates(source_manifest))


def render_proxy_upgrade_harness(source_manifest: dict[str, Any]) -> str:
    """Render a local/fork harness that calls the initializer through the proxy."""

    implementation = _implementation_manifest(source_manifest)
    initializer = _best_initializer(implementation)
    reader = _best_reader(implementation, initializer.get("critical_writes") or [])
    if not initializer or not reader:
        return _sentinel_harness()
    target = _address_literal(_proxy_address(source_manifest))
    args = _solidity_call_args(initializer.get("inputs") or [])
    initializer_signature = _solidity_function_signature(initializer["name"], initializer.get("inputs") or [])
    reader_signature = _solidity_reader_signature(reader)
    reader_type = reader.get("output_type") or "address"
    reader_name = reader["name"]
    comparison = _comparison_assertions(reader_type)
    return "\n".join(
        [
            "// SPDX-License-Identifier: MIT",
            "pragma solidity ^0.8.24;",
            "",
            "interface IVassagoProxyInitializerTarget {",
            f"    {initializer_signature};",
            f"    {reader_signature};",
            "}",
            "",
            "contract VassagoSC01Harness {",
            f"    address constant TARGET = {target};",
            "",
            "    function testProxyInitializerCanChangeProxyState() external {",
            "        IVassagoProxyInitializerTarget target = IVassagoProxyInitializerTarget(TARGET);",
            f"        {reader_type} beforeValue = target.{reader_name}();",
            f"        target.{initializer['name']}({', '.join(args)});",
            f"        {reader_type} afterValue = target.{reader_name}();",
            *comparison,
            "    }",
            "}",
            "",
        ]
    )


def proxy_upgrade_fork(source_manifest: dict[str, Any]) -> dict[str, Any]:
    if not should_use_proxy_upgrade_harness(source_manifest):
        return {}
    chain = ((source_manifest.get("target") or {}).get("chain") or "").lower()
    fork = {
        "requires_rpc_url": True,
        "chain": chain,
        "reason": "proxy initializer impact must be tested against local fork state",
    }
    replay_block = _replay_fork_block(source_manifest)
    if replay_block is not None:
        fork["block_number"] = replay_block
    return fork


def _impact_for_review(
    source_manifest: dict[str, Any],
    review: dict[str, Any],
    proposal_validation: dict[str, Any],
) -> dict[str, Any]:
    base = {
        "source_truth_id": review.get("source_truth_id"),
        "candidate_id": review.get("candidate_id"),
        "thesis_id": review.get("thesis_id"),
        "evidence_kind": review.get("evidence_kind"),
        "runtime_runner": review.get("runtime_runner"),
    }
    if review.get("source_truth_verified") is not True:
        return {
            **base,
            "impact_status": "source_truth_not_verified",
            "impact_ready": False,
            "blockers": ["source_truth_verified_required"],
        }
    if IMPACT_PIECE not in set(review.get("missing_proof_pieces") or []):
        return {
            **base,
            "impact_status": "impact_piece_not_required",
            "impact_ready": False,
            "blockers": [],
        }
    proxy_context = dict(source_manifest.get("proxy_context") or {})
    implementation = _implementation_manifest(source_manifest)
    initializer = _best_initializer(implementation)
    reader = _best_reader(implementation, list(review.get("critical_writes") or []))
    blockers = []
    if not _proxy_address(source_manifest):
        blockers.append("proxy_address_missing")
    if not _implementation_address(source_manifest):
        blockers.append("implementation_address_missing")
    if not implementation:
        blockers.append("implementation_source_missing")
    if not _proxy_delegates(source_manifest):
        blockers.append("proxy_delegatecall_evidence_missing")
    if not initializer:
        blockers.append("implementation_initializer_missing")
    if not reader:
        blockers.append("proxy_callable_reader_missing")
    if blockers:
        return {
            **base,
            "impact_status": "proxy_impact_blocked",
            "impact_ready": False,
            "proxy_context": proxy_context,
            "blockers": sorted(set(blockers)),
            "evidence_refs": _proposal_refs(proposal_validation),
        }
    reader_signature = f"{reader['name']}()"
    return {
        **base,
        "impact_status": "proxy_delegatecall_state_impact_ready",
        "impact_ready": True,
        "impact_kind": "delegatecall_initializer_writes_proxy_storage",
        "proxy_context": proxy_context,
        "execution_address": _proxy_address(source_manifest),
        "implementation_address": _implementation_address(source_manifest),
        "initializer_signature": _signature(initializer["name"], initializer.get("inputs") or []),
        "reader_signature": reader_signature,
        "state_owner": "proxy_storage_via_delegatecall",
        "runtime_strategy": "fork_call_initializer_through_proxy_fallback",
        "runtime_runner": "proxy_upgrade_signature_runtime",
        "measurable_reader": reader_signature,
        "measurable_delta": review.get("measurable_delta") or f"{reader_signature} changes after proxy initializer call",
        "explicit_predicate": review.get("explicit_predicate")
        or f"Unauthorized caller invokes {initializer['name']}(...) through proxy and changes {reader_signature}.",
        "missing_proof_pieces_to_remove": [IMPACT_PIECE],
        "blockers": [],
        "evidence_refs": sorted(
            set(
                [
                    "source:proxy fallback delegatecall",
                    "source:EIP1967 implementation slot or proxy context",
                    f"source:implementation initializer {initializer['name']}",
                    f"abi:reader {reader_signature}",
                    *_proposal_refs(proposal_validation),
                ]
            )
        ),
    }


def _proxy_delegates(source_manifest: dict[str, Any]) -> bool:
    source = _source_text(source_manifest)
    compact = re.sub(r"\s+", "", source)
    return "delegatecall" in source and (
        "_IMPLEMENTATION_SLOT" in source
        or "implementation" in source.lower()
        or "_getAddressSlot" in source
        or "fallback()" in compact
    )


def _best_initializer(implementation: dict[str, Any]) -> dict[str, Any]:
    if not implementation:
        return {}
    source = _source_text(implementation)
    abi = list(implementation.get("abi") or [])
    by_name = {item.get("name"): item for item in abi if item.get("type") == "function"}
    for name in _initializer_names(source, abi):
        body = _function_body(source, name)
        fn = by_name.get(name, {})
        return {
            "name": name,
            "inputs": list(fn.get("inputs") or _source_inputs(source, name)),
            "critical_writes": _critical_writes(body),
        }
    return {}


def _best_reader(implementation: dict[str, Any], writes: list[str]) -> dict[str, Any]:
    abi = list(implementation.get("abi") or [])
    readers = [
        item
        for item in abi
        if item.get("type") == "function"
        and not item.get("inputs")
        and str(item.get("stateMutability") or "") in {"view", "pure"}
    ]
    for write in writes:
        stripped = str(write).lstrip("_")
        names = [stripped, f"get{stripped[:1].upper()}{stripped[1:]}", "owner" if "owner" in stripped.lower() else ""]
        for name in names:
            if not name:
                continue
            for reader in readers:
                if reader.get("name") == name:
                    return _reader_payload(reader)
    for fallback in ("owner", "admin", "implementation"):
        for reader in readers:
            if reader.get("name") == fallback:
                return _reader_payload(reader)
    return {}


def _reader_payload(reader: dict[str, Any]) -> dict[str, Any]:
    outputs = list(reader.get("outputs") or [])
    output_type = str((outputs[0] if outputs else {}).get("type") or "address")
    if output_type not in {"address", "uint256", "uint16", "uint8", "bool"}:
        output_type = "bytes32"
    return {"name": str(reader.get("name") or ""), "output_type": output_type}


def _initializer_names(source: str, abi: list[dict[str, Any]]) -> list[str]:
    names = {
        str(item.get("name"))
        for item in abi
        if item.get("type") == "function" and str(item.get("name") or "").lower().startswith("initialize")
    }
    for match in re.finditer(r"\bfunction\s+([A-Za-z_][A-Za-z0-9_]*)\s*\([^)]*\)(?P<header>[^{;]*)\{", source):
        name = match.group(1)
        header = match.group("header")
        if name.lower().startswith("initialize") or " initializer" in f" {header} ":
            names.add(name)
    return sorted(names)


def _critical_writes(body: str) -> list[str]:
    writes = []
    for match in re.finditer(r"\b(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*[^=]", body):
        name = match.group("name")
        if any(marker in name.lower() for marker in ("owner", "admin", "registry", "implementation", "role")):
            writes.append(name)
    return sorted(set(writes))


def _source_inputs(source: str, name: str) -> list[dict[str, str]]:
    match = re.search(rf"\bfunction\s+{re.escape(name)}\s*\((?P<inputs>[^)]*)\)", source)
    if not match:
        return []
    result = []
    for item in match.group("inputs").split(","):
        parts = [part.strip() for part in item.strip().split() if part.strip()]
        if parts:
            result.append({"type": parts[0]})
    return result


def _solidity_call_args(inputs: list[dict[str, Any]]) -> list[str]:
    args = []
    for item in inputs:
        typ = str(item.get("type") or "")
        if typ == "address":
            args.append("address(this)")
        elif typ.startswith("uint"):
            args.append("1")
        elif typ == "bool":
            args.append("true")
        elif typ == "string":
            args.append('"vassago"')
        else:
            args.append(_zero_value(typ))
    return args


def _solidity_function_signature(name: str, inputs: list[dict[str, Any]]) -> str:
    args = []
    for index, item in enumerate(inputs):
        typ = _solidity_type(str(item.get("type") or "bytes32"))
        args.append(f"{typ} arg{index}")
    return f"function {name}({', '.join(args)}) external"


def _solidity_reader_signature(reader: dict[str, Any]) -> str:
    return f"function {reader['name']}() external view returns ({reader.get('output_type') or 'address'})"


def _solidity_type(typ: str) -> str:
    if typ.startswith("uint") or typ in {"address", "bool", "string", "bytes32"}:
        return typ
    if typ == "bytes":
        return "bytes memory"
    return "bytes32"


def _zero_value(typ: str) -> str:
    if typ == "bytes":
        return 'hex""'
    if typ == "bytes32" or typ.startswith("tuple") or typ.endswith("[]"):
        return "bytes32(0)"
    return "bytes32(0)"


def _comparison_assertions(reader_type: str) -> list[str]:
    if reader_type == "address":
        return [
            '        require(afterValue == address(this), "reader not controlled by caller");',
            '        require(afterValue != beforeValue, "reader unchanged");',
        ]
    if reader_type == "bool":
        return ['        require(afterValue != beforeValue, "reader unchanged");']
    return ['        require(afterValue != beforeValue, "reader unchanged");']


def _address_literal(value: str) -> str:
    normalized = value.lower().removeprefix("0x")
    if len(normalized) == 40 and re.fullmatch(r"[0-9a-f]{40}", normalized):
        return f'address(bytes20(hex"{normalized}"))'
    return "address(0)"


def _signature(name: str, inputs: list[dict[str, Any]]) -> str:
    return f"{name}({','.join(str(item.get('type') or '') for item in inputs)})"


def _proposal_refs(proposal_validation: dict[str, Any]) -> list[str]:
    refs = []
    for item in proposal_validation.get("accepted_proposals") or []:
        refs.extend(str(ref) for ref in item.get("evidence_refs") or [])
    return refs


def _is_proxy_upgrade_review(review: dict[str, Any]) -> bool:
    return review.get("runtime_runner") == "proxy_upgrade_signature_runtime" or review.get("evidence_kind") in {
        "uninitialized_proxy_or_implementation_initializer",
        "uups_authorize_upgrade_weak_or_ambiguous",
    }


def _proxy_address(source_manifest: dict[str, Any]) -> str:
    target = source_manifest.get("target") or {}
    return str(target.get("address") or "")


def _replay_fork_block(source_manifest: dict[str, Any]) -> int | None:
    target = source_manifest.get("target") or {}
    metadata = target.get("metadata") if isinstance(target, dict) else {}
    if not isinstance(metadata, dict):
        return None
    for key in ("replay_fork_block_number", "fork_block_number"):
        value = metadata.get(key)
        try:
            block = int(str(value))
        except (TypeError, ValueError):
            continue
        if block > 0:
            return block
    return None


def _implementation_address(source_manifest: dict[str, Any]) -> str:
    proxy_context = dict(source_manifest.get("proxy_context") or {})
    return str(proxy_context.get("implementation") or "")


def _implementation_manifest(source_manifest: dict[str, Any]) -> dict[str, Any]:
    related = source_manifest.get("related_sources")
    if isinstance(related, dict):
        implementation = related.get("implementation")
        if isinstance(implementation, dict) and implementation.get("status") == "resolved":
            return implementation
    return {}


def _source_text(source_manifest: dict[str, Any]) -> str:
    return "\n".join(str(value) for value in (source_manifest.get("source_files") or {}).values())


def _function_body(source: str, name: str) -> str:
    match = re.search(rf"\bfunction\s+{re.escape(name)}\s*\([^)]*\)[^{{;]*\{{", source)
    if not match:
        return ""
    start = match.end() - 1
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


def _sentinel_harness() -> str:
    return "\n".join(
        [
            "// SPDX-License-Identifier: MIT",
            "pragma solidity ^0.8.24;",
            "contract VassagoSC01Harness {",
            "    function __compileOnlySentinel() external pure returns (bool) { return true; }",
            "}",
            "",
        ]
    )
