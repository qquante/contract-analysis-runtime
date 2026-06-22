from __future__ import annotations

import unittest

from vassago_contract_runtime.sc01_proxy_impact import (
    build_proxy_upgrade_impact_review,
    render_proxy_upgrade_harness,
    should_use_proxy_upgrade_harness,
)


class SC01ProxyImpactTests(unittest.TestCase):
    def test_delegatecall_proxy_initializer_impact_becomes_ready(self) -> None:
        source_manifest = _proxy_manifest(delegatecall=True)
        source_truth = _source_truth_verified()

        review = build_proxy_upgrade_impact_review(source_manifest, source_truth, {})

        self.assertEqual(review["status"], "proxy_impact_ready")
        self.assertEqual(review["impact_ready_count"], 1)
        item = review["reviews"][0]
        self.assertEqual(item["impact_status"], "proxy_delegatecall_state_impact_ready")
        self.assertEqual(item["state_owner"], "proxy_storage_via_delegatecall")
        self.assertEqual(item["execution_address"], "0x1111111111111111111111111111111111111111")
        self.assertEqual(item["reader_signature"], "owner()")
        self.assertEqual(item["missing_proof_pieces_to_remove"], ["proxy_or_implementation_state_impact"])

    def test_missing_delegatecall_blocks_impact(self) -> None:
        review = build_proxy_upgrade_impact_review(_proxy_manifest(delegatecall=False), _source_truth_verified(), {})

        self.assertEqual(review["status"], "blocked")
        self.assertEqual(review["impact_ready_count"], 0)
        self.assertIn("proxy_delegatecall_evidence_missing", review["reviews"][0]["blockers"])

    def test_harness_uses_proxy_address_and_initializer_interface(self) -> None:
        source_manifest = _proxy_manifest(delegatecall=True)

        self.assertTrue(should_use_proxy_upgrade_harness(source_manifest))
        harness = render_proxy_upgrade_harness(source_manifest)

        self.assertIn('address constant TARGET = address(bytes20(hex"1111111111111111111111111111111111111111"));', harness)
        self.assertIn("function initialize(address arg0, address arg1, uint16 arg2, address arg3) external", harness)
        self.assertIn("function owner() external view returns (address)", harness)
        self.assertIn("target.initialize(address(this), address(this), 1, address(this));", harness)
        self.assertIn("testProxyInitializerCanChangeProxyState", harness)


def _source_truth_verified() -> dict:
    return {
        "reviews": [
            {
                "source_truth_id": "ST-test",
                "candidate_id": "TC-test",
                "thesis_id": "uninitialized_implementation_proxy",
                "source_truth_verified": True,
                "runtime_runner": "proxy_upgrade_signature_runtime",
                "evidence_kind": "uninitialized_proxy_or_implementation_initializer",
                "missing_proof_pieces": ["proxy_or_implementation_state_impact"],
                "critical_writes": ["owner", "registry"],
                "measurable_reader": "owner()",
                "measurable_delta": "owner() changes after unauthorized initializer call",
                "explicit_predicate": "Unauthorized caller invokes initialize(...) and changes owner().",
            }
        ]
    }


def _proxy_manifest(*, delegatecall: bool) -> dict:
    proxy_body = """
    contract Proxy {
        bytes32 internal constant _IMPLEMENTATION_SLOT = bytes32(uint256(1));
        constructor(address logic) { logic; }
        fallback() external payable {
            address implementation = address(0x2222222222222222222222222222222222222222);
    """
    if delegatecall:
        proxy_body += """
            assembly {
                let result := delegatecall(gas(), implementation, 0, calldatasize(), 0, 0)
                result
            }
        }
    }
        """
    else:
        proxy_body += """
        }
    }
        """
    return {
        "target": {"chain": "eth", "address": "0x1111111111111111111111111111111111111111"},
        "status": "resolved",
        "abi": [{"type": "fallback", "stateMutability": "payable"}],
        "proxy_context": {
            "proxy": "1",
            "implementation": "0x2222222222222222222222222222222222222222",
        },
        "source_files": {"Proxy.sol": proxy_body},
        "related_sources": {
            "implementation": {
                "status": "resolved",
                "abi": [
                    {
                        "type": "function",
                        "name": "initialize",
                        "inputs": [
                            {"type": "address"},
                            {"type": "address"},
                            {"type": "uint16"},
                            {"type": "address"},
                        ],
                        "outputs": [],
                        "stateMutability": "nonpayable",
                    },
                    {
                        "type": "function",
                        "name": "owner",
                        "inputs": [],
                        "outputs": [{"type": "address"}],
                        "stateMutability": "view",
                    },
                ],
                "source_files": {
                    "Vault.sol": """
                    contract Vault {
                        address public owner;
                        address public registry;
                        uint16 public vaultVersion;
                        address public baseCurrency;
                        function initialize(address owner_, address registry_, uint16 vaultVersion_, address baseCurrency_) external {
                            owner = owner_;
                            registry = registry_;
                            vaultVersion = vaultVersion_;
                            baseCurrency = baseCurrency_;
                        }
                    }
                    """
                },
            }
        },
    }
