from __future__ import annotations

import unittest

from vassago_contract_runtime.sc01_proxy_upgrade import evaluate_proxy_upgrade_signature


class SC01ProxyUpgradeMapperTests(unittest.TestCase):
    def test_transparent_proxy_admin_path_rejects_uups_thesis(self) -> None:
        result = evaluate_proxy_upgrade_signature(
            {
                "abi": _transparent_proxy_abi(),
                "source_files": {
                    "TransparentUpgradeableProxy.sol": """
                    pragma solidity ^0.8.20;
                    contract TransparentUpgradeableProxy {
                        bytes32 internal constant IMPLEMENTATION_SLOT = bytes32(uint256(1));
                        modifier ifAdmin() {
                            if (msg.sender == _getAdmin()) { _; } else { _fallback(); }
                        }
                        function _getAdmin() internal view returns (address) {}
                        function _fallback() internal {}
                        function upgradeTo(address newImplementation) external ifAdmin {}
                        function upgradeToAndCall(address newImplementation, bytes memory data) external payable ifAdmin {}
                    }
                    """,
                },
            },
            "uups_weak_auth",
            ["upgradeTo(address)", "upgradeToAndCall(address,bytes)"],
        )

        self.assertEqual(result["status"], "source_truth_rejected")
        self.assertEqual(result["classification"], "transparent_proxy_admin_path")

    def test_proxy_admin_functions_without_initializer_reject_uninitialized_thesis(self) -> None:
        result = evaluate_proxy_upgrade_signature(
            {
                "abi": _transparent_proxy_abi(),
                "source_files": {
                    "AdminProxy.sol": """
                    pragma solidity ^0.8.20;
                    contract AdminProxy {
                        modifier ifAdmin() { if (msg.sender == _admin()) { _; } else { _fallback(); } }
                        function _admin() internal view returns (address) {}
                        function _fallback() internal {}
                        function admin() external ifAdmin returns (address) {}
                        function implementation() external ifAdmin returns (address) {}
                        function upgradeTo(address newImplementation) external ifAdmin {}
                    }
                    """,
                },
            },
            "uninitialized_implementation_proxy",
            ["admin()", "implementation()", "upgradeTo(address)"],
        )

        self.assertEqual(result["status"], "source_truth_rejected")
        self.assertEqual(result["classification"], "transparent_proxy_admin_path")

    def test_proxy_with_missing_implementation_source_blocks_initializer_truth(self) -> None:
        result = evaluate_proxy_upgrade_signature(
            {
                "abi": [{"type": "function", "name": "initialize", "inputs": [{"type": "address"}]}],
                "proxy_context": {
                    "proxy": "1",
                    "implementation": "0x1111111111111111111111111111111111111111",
                },
                "source_files": {
                    "Proxy.sol": """
                    pragma solidity ^0.8.20;
                    contract Proxy { fallback() external payable { address impl = address(0); } }
                    """,
                },
            },
            "uninitialized_implementation_proxy",
            ["initialize(address)"],
        )

        self.assertEqual(result["status"], "source_truth_blocked_proxy_upgrade_mapper")
        self.assertEqual(result["classification"], "proxy_implementation_source_missing")
        self.assertIn("implementation_source_required", result["missing_proof_pieces"])

    def test_initializer_with_critical_write_and_reader_verifies_but_blocks_runtime_impact(self) -> None:
        result = evaluate_proxy_upgrade_signature(
            {
                "abi": [],
                "proxy_context": {
                    "proxy": "1",
                    "implementation": "0x2222222222222222222222222222222222222222",
                },
                "source_files": {
                    "Proxy.sol": "contract Proxy { fallback() external payable {} }",
                },
                "related_sources": {
                    "implementation": {
                        "status": "resolved",
                        "abi": [
                            {
                                "type": "function",
                                "name": "initialize",
                                "inputs": [{"type": "address"}, {"type": "address"}],
                            },
                            {"type": "function", "name": "owner", "inputs": []},
                            {"type": "function", "name": "registry", "inputs": []},
                        ],
                        "source_files": {
                            "Impl.sol": """
                            pragma solidity ^0.8.20;
                            contract Impl {
                                address public owner;
                                address public registry;
                                function initialize(address newOwner, address newRegistry) external {
                                    owner = newOwner;
                                    registry = newRegistry;
                                }
                            }
                            """,
                        },
                    },
                },
            },
            "uninitialized_implementation_proxy",
            ["initialize(address,address)"],
        )

        self.assertEqual(result["status"], "source_truth_verified")
        self.assertEqual(result["classification"], "uninitialized_proxy_or_implementation_initializer")
        self.assertIn("proxy_or_implementation_state_impact", result["missing_proof_pieces"])
        self.assertEqual(result["codable_args"], ["address(this)", "address(this)"])
        self.assertEqual(result["measurable_reader"], "owner()")

    def test_initializer_with_tuple_arg_requires_arg_builder(self) -> None:
        result = evaluate_proxy_upgrade_signature(
            {
                "abi": [
                    {
                        "type": "function",
                        "name": "initialize",
                        "inputs": [{"type": "tuple"}, {"type": "address"}],
                    },
                    {"type": "function", "name": "owner", "inputs": []},
                ],
                "proxy_context": {
                    "proxy": "1",
                    "implementation": "0x2222222222222222222222222222222222222222",
                },
                "source_files": {
                    "Proxy.sol": "contract Proxy { fallback() external payable {} }",
                },
                "related_sources": {
                    "implementation": {
                        "status": "resolved",
                        "abi": [
                            {
                                "type": "function",
                                "name": "initialize",
                                "inputs": [{"type": "tuple"}, {"type": "address"}],
                            },
                            {"type": "function", "name": "owner", "inputs": []},
                        ],
                        "source_files": {
                            "Impl.sol": """
                            pragma solidity ^0.8.20;
                            contract Impl {
                                address public owner;
                                struct InitConfig { address owner; }
                                function initialize(InitConfig memory cfg, address registry) external {
                                    owner = cfg.owner;
                                }
                            }
                            """,
                        },
                    }
                },
            },
            "uninitialized_implementation_proxy",
            ["initialize((address),address)"],
        )

        self.assertEqual(result["status"], "source_truth_verified")
        self.assertIn("codable_initializer_args", result["missing_proof_pieces"])
        self.assertEqual(result["codable_args"], [])

    def test_protected_authorize_upgrade_rejects_uups_thesis(self) -> None:
        result = evaluate_proxy_upgrade_signature(
            {
                "abi": [{"type": "function", "name": "upgradeTo", "inputs": [{"type": "address"}]}],
                "source_files": {
                    "Impl.sol": """
                    pragma solidity ^0.8.20;
                    contract Impl {
                        modifier onlyOwner() { _; }
                        function upgradeTo(address newImplementation) external {}
                        function _authorizeUpgrade(address newImplementation) internal onlyOwner {}
                    }
                    """,
                },
            },
            "uups_weak_auth",
            ["upgradeTo(address)"],
        )

        self.assertEqual(result["status"], "source_truth_rejected")
        self.assertEqual(result["classification"], "authorize_upgrade_protected")

    def test_weak_authorize_upgrade_verifies_but_requires_upgrade_target_and_state_reader(self) -> None:
        result = evaluate_proxy_upgrade_signature(
            {
                "abi": [
                    {"type": "function", "name": "upgradeTo", "inputs": [{"type": "address"}]},
                    {"type": "function", "name": "implementation", "inputs": []},
                ],
                "source_files": {
                    "Impl.sol": """
                    pragma solidity ^0.8.20;
                    contract Impl {
                        function implementation() external view returns (address) {}
                        function upgradeTo(address newImplementation) external {}
                        function _authorizeUpgrade(address newImplementation) internal {}
                    }
                    """,
                },
            },
            "uups_weak_auth",
            ["upgradeTo(address)"],
        )

        self.assertEqual(result["status"], "source_truth_verified")
        self.assertEqual(result["classification"], "uups_authorize_upgrade_weak_or_ambiguous")
        self.assertIn("upgrade_target_contract", result["missing_proof_pieces"])
        self.assertIn("proxy_state_reader", result["missing_proof_pieces"])


def _transparent_proxy_abi() -> list[dict[str, object]]:
    return [
        {"type": "function", "name": "admin", "inputs": []},
        {"type": "function", "name": "implementation", "inputs": []},
        {"type": "function", "name": "changeAdmin", "inputs": [{"type": "address"}]},
        {"type": "function", "name": "upgradeTo", "inputs": [{"type": "address"}]},
        {
            "type": "function",
            "name": "upgradeToAndCall",
            "inputs": [{"type": "address"}, {"type": "bytes"}],
        },
    ]
