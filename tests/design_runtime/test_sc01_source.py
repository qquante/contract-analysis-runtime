from __future__ import annotations

import json
import unittest
from pathlib import Path

from vassago_contract_runtime.sc01_source import evaluate_public_normal_behavior, evaluate_uninitialized_uups_initializer


class SC01SourceVerifierTests(unittest.TestCase):
    def test_positive_fixture_verifies_without_metadata_shortcut(self) -> None:
        fixture = json.loads(Path("tests/fixtures/source_fixture_positive.json").read_text())["targets"][0]

        result = evaluate_uninitialized_uups_initializer(fixture)

        self.assertTrue(result["verified"])
        self.assertEqual(result["admin_reader"], "owner()")
        self.assertEqual(result["admin_variable"], "owner")
        self.assertEqual(result["codable_args"], [])
        self.assertNotIn("disable_initializers_present", result["blockers"])

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


if __name__ == "__main__":
    unittest.main()
