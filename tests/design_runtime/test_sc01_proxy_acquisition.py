from __future__ import annotations

import unittest

from vassago_contract_runtime.sc01_proxy_acquisition import build_proxy_upgrade_candidates


class SC01ProxyAcquisitionTests(unittest.TestCase):
    def test_proxy_related_initializer_queues_uninitialized_thesis(self) -> None:
        candidates = build_proxy_upgrade_candidates(
            target_id="CT-proxy",
            chain="eth",
            address="0x1111111111111111111111111111111111111111",
            function_index={
                "functions": [
                    {"name": "initialize", "inputs": [{"type": "address"}], "source_relation": "proxy_implementation"}
                ]
            },
            source_manifest={
                "proxy_context": {"proxy": "1", "implementation": "0x2222222222222222222222222222222222222222"},
                "source_files": {"Proxy.sol": "contract Proxy { fallback() external payable {} }"},
                "related_sources": {
                    "implementation": {
                        "status": "resolved",
                        "source_files": {"Impl.sol": "contract Impl { function initialize(address owner) external {} }"},
                    }
                },
            },
            access_surface={
                "functions": [
                    {
                        "signature": "initialize(address)",
                        "source_status": "found",
                        "extraction_source": "abi_source_heuristic",
                    }
                ]
            },
        )

        self.assertEqual({item["thesis_id"] for item in candidates}, {"uninitialized_implementation_proxy"})
        self.assertIn("proxy_context", candidates[0]["matched_motifs"])
        self.assertIn("related_implementation", candidates[0]["matched_motifs"])

    def test_transparent_proxy_upgrade_queues_uups_for_source_truth_rejection(self) -> None:
        candidates = build_proxy_upgrade_candidates(
            target_id="CT-transparent",
            chain="eth",
            address="0x1111111111111111111111111111111111111111",
            function_index={
                "functions": [
                    {"name": "upgradeTo", "inputs": [{"type": "address"}]},
                    {"name": "upgradeToAndCall", "inputs": [{"type": "address"}, {"type": "bytes"}]},
                    {"name": "admin", "inputs": []},
                ]
            },
            source_manifest={
                "source_files": {
                    "Proxy.sol": """
                    contract TransparentUpgradeableProxy {
                        bytes32 internal constant IMPLEMENTATION_SLOT = bytes32(uint256(1));
                        modifier ifAdmin() { if (msg.sender == _getAdmin()) { _; } else { _fallback(); } }
                        function _getAdmin() internal view returns (address) {}
                        function _fallback() internal {}
                        function upgradeTo(address newImplementation) external ifAdmin {}
                        function upgradeToAndCall(address newImplementation, bytes memory data) external payable ifAdmin {}
                    }
                    """,
                }
            },
            access_surface={
                "functions": [
                    {"signature": "upgradeTo(address)", "source_status": "found", "extraction_source": "abi_source"},
                    {
                        "signature": "upgradeToAndCall(address,bytes)",
                        "source_status": "found",
                        "extraction_source": "abi_source",
                    },
                ]
            },
        )

        uups = next(item for item in candidates if item["thesis_id"] == "uups_weak_auth")
        self.assertIn("TransparentUpgradeableProxy", uups["matched_motifs"])
        self.assertIn("EIP-1967", uups["matched_motifs"])

    def test_access_control_role_readers_queue_role_admin_escalation(self) -> None:
        candidates = build_proxy_upgrade_candidates(
            target_id="CT-role",
            chain="eth",
            address="0x1111111111111111111111111111111111111111",
            function_index={
                "functions": [
                    {"name": "grantRole", "inputs": [{"type": "bytes32"}, {"type": "address"}]},
                    {"name": "hasRole", "inputs": [{"type": "bytes32"}, {"type": "address"}]},
                    {"name": "getRoleAdmin", "inputs": [{"type": "bytes32"}]},
                ]
            },
            source_manifest={
                "source_files": {
                    "Access.sol": """
                    contract Access {
                        bytes32 public constant DEFAULT_ADMIN_ROLE = 0x00;
                        function hasRole(bytes32 role, address account) external view returns (bool) {}
                        function getRoleAdmin(bytes32 role) external view returns (bytes32) {}
                        function grantRole(bytes32 role, address account) external {}
                    }
                    """,
                }
            },
            access_surface={"functions": []},
        )

        self.assertEqual({item["thesis_id"] for item in candidates}, {"role_admin_escalation"})
