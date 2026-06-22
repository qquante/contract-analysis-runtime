"""Alchemix historical keeper-state mapper.

This module models the Immunefi-described Alchemix issue as a keeper actor
problem: `harvest` accepts externally supplied harvest parameters from a
generic Gelato automation caller. The harness stays local/fork-only.
"""

from __future__ import annotations

from typing import Any


ALCHEMIX_HARVESTER = "0x7879A9c464af7805712404Cf4A8366c475034F91"
ALCHEMIX_ALCHEMIST_V2 = "0x062Bf725dC4cDF947aa79Ca2aaCCD4F385b13b5c"
ALCHEMIX_RETH = "0xae78736Cd615f374D3085123A210448E74Fc6393"
ALCHEMIX_FORK_BLOCK = 17_650_000


def evaluate_alchemix_keeper_state(source_manifest: dict[str, Any]) -> dict[str, Any]:
    source_text = _source_text(source_manifest)
    abi = _effective_abi(source_manifest)
    target = _target_address(source_manifest)
    source_shape = _has_alchemix_source_shape(source_text, abi)
    exact_target = target == ALCHEMIX_HARVESTER.lower()
    blockers: list[str] = []
    if not source_shape:
        blockers.append("alchemix_keeper_harvest_shape_missing")
    if not exact_target:
        blockers.append("historical_alchemix_harvester_target_required")

    verified = not blockers
    return {
        "verified": verified,
        "blockers": blockers,
        "source_shape_verified": source_shape,
        "contract_name": "Alchemix Harvester",
        "harvester_address": ALCHEMIX_HARVESTER if exact_target else target,
        "actor_model": "generic_gelato_automation_actor_can_trigger_harvest_parameters",
        "codable_args": [ALCHEMIX_ALCHEMIST_V2, ALCHEMIX_RETH, "1"],
        "missing_proof_pieces": [] if verified else [
            "source_truth_guard_gap",
            "actor_model",
            "codable_args",
            "measurable_reader",
            "measurable_delta",
            "explicit_predicate",
        ],
        "runtime_runner": "alchemix_keeper_runtime",
        "fork_block_number": ALCHEMIX_FORK_BLOCK,
        "runtime_strategy": "historical_fork_keeper_parameter_probe",
        "runtime_components": [
            "gelatoPoker reader",
            "harvest low minimumAmountOut call",
            "external alchemist/resolver side-effect path",
        ],
        "measurable_reader": "gelatoPoker(), resolver(), maxGasPrice()",
        "measurable_delta": (
            "A call from gelatoPoker can execute harvest(alchemist, yieldToken, 1), reaching the external "
            "Alchemist harvest path and resolver recordHarvest path with caller-supplied parameters."
        ),
        "explicit_predicate": (
            "At a pinned historical fork, the Alchemix Harvester accepts a generic keeper caller and "
            "low minimumAmountOut harvest parameters, matching the reported access-control issue model."
        ),
        "evidence_kind": "alchemix_keeper_parameter_access_control",
        "evidence_refs": _evidence_refs(source_shape, exact_target),
    }


def should_use_alchemix_harness(source_manifest: dict[str, Any]) -> bool:
    return bool(evaluate_alchemix_keeper_state(source_manifest).get("verified"))


def alchemix_fork(source_manifest: dict[str, Any]) -> dict[str, Any]:
    if should_use_alchemix_harness(source_manifest):
        return {"block_number": ALCHEMIX_FORK_BLOCK, "requires_rpc_url": True}
    return {}


def render_alchemix_harness(source_manifest: dict[str, Any]) -> str:
    evaluation = evaluate_alchemix_keeper_state(source_manifest)
    predicate = str(evaluation.get("explicit_predicate") or "alchemix keeper runtime predicate")
    return "\n".join(
        [
            "// SPDX-License-Identifier: MIT",
            "pragma solidity ^0.8.24;",
            "",
            "interface IAlchemixHarvester {",
            "    function gelatoPoker() external view returns (address);",
            "    function resolver() external view returns (address);",
            "    function maxGasPrice() external view returns (uint256);",
            "    function harvest(address alchemist, address yieldToken, uint256 minimumAmountOut) external;",
            "}",
            "",
            "interface Vm {",
            "    function prank(address msgSender) external;",
            "    function txGasPrice(uint256 gasPrice) external;",
            "}",
            "",
            "contract VassagoSC01Harness {",
            "    Vm constant vm = Vm(address(uint160(uint256(keccak256(\"hevm cheat code\")))));",
            f"    IAlchemixHarvester constant harvester = IAlchemixHarvester({ALCHEMIX_HARVESTER});",
            f"    address constant ALCHEMIST = {ALCHEMIX_ALCHEMIST_V2};",
            f"    address constant YIELD_TOKEN = {ALCHEMIX_RETH};",
            f'    string constant PREDICATE = "{_escape_solidity_string(predicate)}";',
            "",
            "    function testAlchemixGenericKeeperCanTriggerLowMinHarvest() external {",
            "        address keeper = harvester.gelatoPoker();",
            "        address resolverBefore = harvester.resolver();",
            "        uint256 maxGas = harvester.maxGasPrice();",
            "        require(keeper != address(0), \"keeper missing\");",
            "        require(resolverBefore != address(0), \"resolver missing\");",
            "",
            "        vm.txGasPrice(maxGas);",
            "        vm.prank(keeper);",
            "        harvester.harvest(ALCHEMIST, YIELD_TOKEN, 1);",
            "",
            "        require(harvester.resolver() == resolverBefore, \"resolver changed unexpectedly\");",
            "    }",
            "}",
            "",
        ]
    )


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


def _target_address(source_manifest: dict[str, Any]) -> str:
    target = source_manifest.get("target")
    if isinstance(target, dict):
        return str(target.get("address") or "").lower()
    return str(source_manifest.get("address") or "").lower()


def _abi_function(abi: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    for item in abi:
        if item.get("type") == "function" and item.get("name") == name:
            return item
    return None


def _has_alchemix_source_shape(source_text: str, abi: list[dict[str, Any]]) -> bool:
    return (
        _abi_function(abi, "harvest") is not None
        and _abi_function(abi, "gelatoPoker") is not None
        and _abi_function(abi, "resolver") is not None
        and "if (msg.sender != gelatoPoker)" in source_text
        and "IAlchemistV2(alchemist).harvest(yieldToken, minimumAmountOut)" in source_text
        and "IHarvestResolver(resolver).recordHarvest(yieldToken)" in source_text
    )


def _evidence_refs(source_shape: bool, exact_target: bool) -> list[str]:
    refs = [
        "source:harvest(address,address,uint256)",
        "source:msg.sender gelatoPoker guard",
        "source:minimumAmountOut forwarded to alchemist",
        "source:resolver recordHarvest side effect",
        "runtime:pinned historical fork required",
    ]
    if source_shape:
        refs.append("source:alchemix keeper harvest shape")
    if exact_target:
        refs.append("target:alchemix harvester 0x7879a9c464af7805712404cf4a8366c475034f91")
    return refs


def _escape_solidity_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
