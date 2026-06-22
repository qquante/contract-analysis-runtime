from __future__ import annotations

import json
import unittest
from pathlib import Path

from vassago_contract_runtime.sc01_source import (
    evaluate_access_control_initializer,
    evaluate_known_non_sc01_pattern,
    evaluate_public_normal_behavior,
    evaluate_uninitialized_uups_initializer,
)
from vassago_contract_runtime.phases.compile_only import render_sc01_harness


class SC01SourceVerifierTests(unittest.TestCase):
    def test_positive_fixture_verifies_without_metadata_shortcut(self) -> None:
        fixture = json.loads(Path("tests/fixtures/source_fixture_positive.json").read_text())["targets"][0]

        result = evaluate_uninitialized_uups_initializer(fixture)

        self.assertTrue(result["verified"])
        self.assertEqual(result["admin_reader"], "owner()")
        self.assertEqual(result["admin_variable"], "owner")
        self.assertEqual(result["codable_args"], [])
        self.assertNotIn("disable_initializers_present", result["blockers"])

    def test_access_control_initializer_with_address_array_is_source_verified(self) -> None:
        fixture = {
            "abi": [
                {
                    "type": "function",
                    "name": "DEFAULT_ADMIN_ROLE",
                    "inputs": [],
                    "outputs": [{"type": "bytes32"}],
                    "stateMutability": "view",
                },
                {
                    "type": "function",
                    "name": "hasRole",
                    "inputs": [{"type": "bytes32"}, {"type": "address"}],
                    "outputs": [{"type": "bool"}],
                    "stateMutability": "view",
                },
                {
                    "type": "function",
                    "name": "initialize",
                    "inputs": [{"name": "admin", "type": "address"}, {"name": "accounts", "type": "address[]"}],
                    "outputs": [],
                    "stateMutability": "nonpayable",
                },
            ],
            "metadata": {"contract_name": "GatedProxyLike"},
            "source_files": {
                "GatedProxyLike.sol": """
                pragma solidity 0.6.12;
                contract GatedProxyLike {
                    bytes32 public constant DEFAULT_ADMIN_ROLE = 0x00;
                    bytes32 public constant APPROVED_ACCOUNT_ROLE = keccak256("APPROVED_ACCOUNT_ROLE");
                    modifier initializer() { _; }
                    function hasRole(bytes32 role, address account) public view returns (bool) {}
                    function _setupRole(bytes32 role, address account) internal {}
                    function initialize(address admin, address[] memory accounts) external initializer {
                        _setupRole(DEFAULT_ADMIN_ROLE, admin);
                        for (uint256 i = 0; i < accounts.length; i++) {
                            _setupRole(APPROVED_ACCOUNT_ROLE, accounts[i]);
                        }
                    }
                }
                """,
            },
        }

        result = evaluate_access_control_initializer(fixture)
        harness = render_sc01_harness(fixture)

        self.assertTrue(result["verified"], result["blockers"])
        self.assertEqual(result["codable_args"], ["address(this)", "vassagoAccounts1"])
        self.assertIn("address[] memory vassagoAccounts1 = new address[](1);", harness)
        self.assertIn("target.initialize(address(this), vassagoAccounts1);", harness)
        self.assertIn("target.hasRole(target.DEFAULT_ADMIN_ROLE(), address(this))", harness)

    def test_disable_initializers_blocks_verification(self) -> None:
        fixture = json.loads(Path("tests/fixtures/source_fixture_positive.json").read_text())["targets"][0]
        source = fixture["source_files"]["FixtureUUPSPositive.sol"]
        fixture["source_files"]["FixtureUUPSPositive.sol"] = source.replace(
            "event Upgraded(address indexed implementation);",
            "event Upgraded(address indexed implementation); constructor() { _disableInitializers(); }",
        )

        result = evaluate_uninitialized_uups_initializer(fixture)

        self.assertFalse(result["verified"])
        self.assertIn("disable_initializers_present", result["blockers"])

    def test_missing_reader_blocks_verification(self) -> None:
        fixture = json.loads(Path("tests/fixtures/source_fixture_positive.json").read_text())["targets"][0]
        fixture["abi"] = [item for item in fixture["abi"] if item.get("name") != "owner"]
        fixture["source_files"]["FixtureUUPSPositive.sol"] = fixture["source_files"]["FixtureUUPSPositive.sol"].replace(
            "address public owner;",
            "address private owner;",
        )

        result = evaluate_uninitialized_uups_initializer(fixture)

        self.assertFalse(result["verified"])
        self.assertIn("admin_reader_missing", result["blockers"])

    def test_public_accounting_function_is_rejected_as_normal_behavior(self) -> None:
        fixture = json.loads(Path("tests/fixtures/source_fixture_negative.json").read_text())["targets"][0]

        result = evaluate_public_normal_behavior(fixture, ["initializeMarket"])

        self.assertTrue(result["rejected"])
        self.assertEqual(result["classification"], "caller_funded_accounting")

    def test_public_normal_behavior_handles_plain_assignment_without_regex_error(self) -> None:
        fixture = {
            "abi": [],
            "source_files": {
                "PlainAssignment.sol": """
                pragma solidity ^0.8.20;
                contract PlainAssignment {
                    uint256 public value;
                    function setValue(uint256 newValue) external {
                        value = newValue;
                    }
                }
                """,
            },
        }

        result = evaluate_public_normal_behavior(fixture, ["setValue"])

        self.assertFalse(result["rejected"])
        self.assertIn("no_public_normal_behavior_policy_matched", result["blockers"])

    def test_admin_write_is_not_rejected_as_public_normal_behavior(self) -> None:
        fixture = json.loads(Path("tests/fixtures/source_fixture_positive.json").read_text())["targets"][0]

        result = evaluate_public_normal_behavior(fixture, ["initialize"])

        self.assertFalse(result["rejected"])
        self.assertIn("admin_variable_write_present", result["blockers"])

    def test_transparent_proxy_admin_upgrade_is_not_uups_weak_auth(self) -> None:
        fixture = {
            "abi": [],
            "source_files": {
                "Proxy.sol": """
                pragma solidity ^0.4.24;
                contract Proxy {
                    bytes32 private constant IMPLEMENTATION_SLOT = 0x0;
                    bytes32 private constant ADMIN_SLOT = 0x0;
                    modifier ifAdmin() { if (msg.sender == _admin()) { _; } else { _fallback(); } }
                    function _admin() internal view returns (address adm) {}
                    function _setImplementation(address newImplementation) internal {}
                    function _upgradeTo(address newImplementation) internal { _setImplementation(newImplementation); }
                    function upgradeTo(address newImplementation) external ifAdmin { _upgradeTo(newImplementation); }
                    function upgradeToAndCall(address newImplementation, bytes data) payable external ifAdmin {
                        _upgradeTo(newImplementation);
                        require(address(this).call.value(msg.value)(data));
                    }
                    function _fallback() internal {}
                }
                """,
            },
        }

        result = evaluate_known_non_sc01_pattern(fixture, "uups_weak_auth", ["upgradeTo", "upgradeToAndCall"])

        self.assertTrue(result["rejected"])
        self.assertEqual(result["classification"], "transparent_proxy_admin_path")

    def test_immutable_admin_proxy_upgrade_is_not_uups_weak_auth(self) -> None:
        fixture = {
            "abi": [],
            "source_files": {
                "Proxy.sol": """
                pragma solidity ^0.8.10;
                contract Proxy {
                    address immutable _admin;
                    modifier ifAdmin() { if (msg.sender == _admin) { _; } else { _fallback(); } }
                    function _setImplementation(address newImplementation) internal {}
                    function _upgradeTo(address newImplementation) internal { _setImplementation(newImplementation); }
                    function admin() external ifAdmin returns (address) { return _admin; }
                    function upgradeTo(address newImplementation) external ifAdmin { _upgradeTo(newImplementation); }
                    function _fallback() internal {}
                }
                """,
            },
        }

        result = evaluate_known_non_sc01_pattern(fixture, "uups_weak_auth", ["upgradeTo"])

        self.assertTrue(result["rejected"])
        self.assertEqual(result["classification"], "transparent_proxy_admin_path")

    def test_pool_initializer_is_protocol_initializer_not_admin_initializer(self) -> None:
        fixture = {
            "abi": [],
            "source_files": {
                "PoolManager.sol": """
                pragma solidity ^0.8.26;
                struct PoolKey { address currency0; address currency1; uint24 fee; int24 tickSpacing; address hooks; }
                contract PoolManager {
                    event Initialize(bytes32 id, address currency0, address currency1, uint24 fee, int24 tickSpacing, address hooks, uint160 sqrtPriceX96, int24 tick);
                    function initialize(PoolKey memory key, uint160 sqrtPriceX96) external returns (int24 tick) {
                        bytes32 id = keccak256(abi.encode(key));
                        emit Initialize(id, key.currency0, key.currency1, key.fee, key.tickSpacing, key.hooks, sqrtPriceX96, tick);
                    }
                }
                """,
            },
        }

        result = evaluate_known_non_sc01_pattern(fixture, "uninitialized_implementation_proxy", ["initialize"])

        self.assertTrue(result["rejected"])
        self.assertEqual(result["classification"], "protocol_pool_initializer")

    def test_public_factory_creation_is_not_proxy_initializer(self) -> None:
        fixture = {
            "abi": [],
            "source_files": {
                "Factory.sol": """
                pragma solidity ^0.5.16;
                contract Factory {
                    mapping(address => mapping(address => address)) public getPair;
                    address[] public allPairs;
                    event PairCreated(address indexed token0, address indexed token1, address pair, uint256);
                    function createPair(address tokenA, address tokenB) external returns (address pair) {
                        bytes memory bytecode = hex"00";
                        bytes32 salt = keccak256(abi.encodePacked(tokenA, tokenB));
                        assembly { pair := create2(0, add(bytecode, 32), mload(bytecode), salt) }
                        getPair[tokenA][tokenB] = pair;
                        allPairs.push(pair);
                        emit PairCreated(tokenA, tokenB, pair, allPairs.length);
                    }
                }
                """,
            },
        }

        result = evaluate_known_non_sc01_pattern(fixture, "uninitialized_implementation_proxy", ["createPair"])

        self.assertTrue(result["rejected"])
        self.assertEqual(result["classification"], "public_factory_or_pool_creation")

    def test_initialized_eip1967_proxy_is_not_uninitialized_initializer_candidate(self) -> None:
        fixture = {
            "abi": [],
            "proxy_context": {
                "proxy": "1",
                "implementation": "0x728a138a4823392c2efa55e028d434f526fe03cf",
            },
            "source_files": {
                "InitializableUpgradeabilityProxy.sol": """
                pragma solidity 0.8.10;
                contract InitializableUpgradeabilityProxy {
                    bytes32 internal constant IMPLEMENTATION_SLOT = 0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc;
                    function _implementation() internal view returns (address impl) {}
                    function _setImplementation(address _logic) internal {}
                    function initialize(address _logic, bytes memory _data) public payable {
                        require(_implementation() == address(0));
                        _setImplementation(_logic);
                        if (_data.length > 0) {
                            (bool success,) = _logic.delegatecall(_data);
                            require(success);
                        }
                    }
                }
                """,
            },
        }

        result = evaluate_known_non_sc01_pattern(
            fixture,
            "uninitialized_implementation_proxy",
            ["initialize(address,bytes)"],
        )

        self.assertTrue(result["rejected"])
        self.assertEqual(result["classification"], "initialized_eip1967_proxy")

    def test_token_approval_operator_is_not_role_admin_escalation(self) -> None:
        fixture = {"abi": [], "source_files": {"Token.sol": "contract Token {}"}}

        result = evaluate_known_non_sc01_pattern(
            fixture,
            "role_admin_escalation",
            [
                "getApproved(uint256)",
                "isApprovedForAll(address,address)",
                "positions(uint256)",
                "setApprovalForAll(address,bool)",
            ],
        )

        self.assertTrue(result["rejected"])
        self.assertEqual(result["classification"], "token_approval_operator")

    def test_caller_scoped_operator_is_public_normal_behavior(self) -> None:
        fixture = {
            "abi": [],
            "source_files": {
                "ERC6909Like.sol": """
                pragma solidity ^0.8.20;
                contract ERC6909Like {
                    mapping(address => mapping(address => bool)) public isOperator;
                    event OperatorSet(address indexed owner, address indexed operator, bool approved);
                    function setOperator(address operator, bool approved) public returns (bool) {
                        isOperator[msg.sender][operator] = approved;
                        emit OperatorSet(msg.sender, operator, approved);
                        return true;
                    }
                }
                """,
            },
        }

        result = evaluate_public_normal_behavior(fixture, ["setOperator"])

        self.assertTrue(result["rejected"])
        self.assertEqual(result["classification"], "caller_scoped_operator")


if __name__ == "__main__":
    unittest.main()
