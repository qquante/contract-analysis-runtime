from __future__ import annotations

import unittest

from vassago_contract_runtime.sc01_proxy_semantics import (
    accepted_semantic_proposals,
    build_proxy_upgrade_dossier,
    build_proxy_upgrade_semantic_proposals,
    validate_proxy_upgrade_semantic_proposals,
)


class SC01ProxySemanticsTests(unittest.TestCase):
    def test_custom_owner_proxy_initializer_proposal_validates_by_effect(self) -> None:
        dossier = build_proxy_upgrade_dossier(
            {
                "proxy_context": {
                    "proxy": "1",
                    "implementation": "0x2222222222222222222222222222222222222222",
                },
                "source_files": {"Proxy.sol": "contract Proxy { fallback() external payable {} }"},
                "related_sources": {
                    "implementation": {
                        "status": "resolved",
                        "abi": [
                            {"type": "function", "name": "initialize", "inputs": [{"type": "address"}]},
                            {
                                "type": "function",
                                "name": "ownerProxy1",
                                "inputs": [],
                                "stateMutability": "view",
                            },
                        ],
                        "source_files": {
                            "Impl.sol": """
                            contract Impl {
                                address public ownerProxy1;
                                function initialize(address who) external { ownerProxy1 = who; }
                            }
                            """,
                        },
                    }
                },
            },
            {"queue": [{"thesis_id": "uninitialized_implementation_proxy"}]},
        )

        proposals = build_proxy_upgrade_semantic_proposals(dossier)
        validation = validate_proxy_upgrade_semantic_proposals(dossier, proposals)
        accepted = accepted_semantic_proposals(validation, "initializer_semantic_mapping")

        self.assertEqual(validation["accepted_count"], 1)
        self.assertEqual(accepted[0]["semantic_payload"]["critical_writes"], ["ownerProxy1"])
        self.assertEqual(accepted[0]["semantic_payload"]["measurable_reader"], "ownerProxy1()")

    def test_weak_authorize_upgrade_proposal_requires_source_function_and_reader(self) -> None:
        dossier = build_proxy_upgrade_dossier(
            {
                "proxy_context": {
                    "proxy": "1",
                    "implementation": "0x2222222222222222222222222222222222222222",
                },
                "source_files": {"Proxy.sol": "contract Proxy { fallback() external payable {} }"},
                "related_sources": {
                    "implementation": {
                        "status": "resolved",
                        "abi": [
                            {"type": "function", "name": "upgradeTo", "inputs": [{"type": "address"}]},
                            {
                                "type": "function",
                                "name": "implementation",
                                "inputs": [],
                                "stateMutability": "view",
                            },
                        ],
                        "source_files": {
                            "Impl.sol": """
                            contract Impl {
                                function implementation() external view returns (address) {}
                                function upgradeTo(address newImplementation) external {}
                                function _authorizeUpgrade(address newImplementation) internal {}
                            }
                            """,
                        },
                    }
                },
            },
            {"queue": [{"thesis_id": "uups_weak_auth"}]},
        )

        proposals = build_proxy_upgrade_semantic_proposals(dossier)
        validation = validate_proxy_upgrade_semantic_proposals(dossier, proposals)
        accepted = accepted_semantic_proposals(validation, "uups_authorize_upgrade_mapping")

        self.assertEqual(len(accepted), 1)
        self.assertEqual(accepted[0]["semantic_payload"]["semantic_role"], "upgrade_authorizer")
        self.assertEqual(accepted[0]["semantic_payload"]["measurable_reader"], "implementation()")


if __name__ == "__main__":
    unittest.main()
