from __future__ import annotations

import unittest

from vassago_contract_runtime.design_runtime.models import (
    ArtifactSpec,
    ContractTarget,
    DesignSpec,
    GateSpec,
    ModelValidationError,
    PhaseSpec,
    RunOptions,
)


class ModelTests(unittest.TestCase):
    def test_contract_target_normalizes_and_derives_stable_id(self) -> None:
        target = ContractTarget(chain="ETH", address="0xABCDEFabcdefABCDEFabcdefABCDEFabcdefABCD")

        self.assertEqual(target.chain, "eth")
        self.assertEqual(target.address, "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd")
        self.assertTrue(target.target_id.startswith("CT-"))
        self.assertEqual(target.target_id, ContractTarget.from_json(target.to_json()).target_id)

    def test_contract_target_rejects_invalid_address(self) -> None:
        with self.assertRaises(ModelValidationError) as error:
            ContractTarget(chain="eth", address="0x123")

        self.assertEqual(error.exception.code, "invalid_address")

    def test_phase_id_validation(self) -> None:
        with self.assertRaises(ModelValidationError) as error:
            PhaseSpec(phase_id="intake", name="Intake")

        self.assertEqual(error.exception.code, "invalid_phase_id")

    def test_design_roundtrip(self) -> None:
        design = DesignSpec(
            design_id="sc01-access",
            version="v0.1.0",
            title="SC01",
            target_model="ContractTarget",
            evidence_policy={"no_broadcast": True},
            phases=(
                PhaseSpec(
                    phase_id="00_intake",
                    name="Intake",
                    outputs=(ArtifactSpec("target-manifest.json"),),
                ),
                PhaseSpec(
                    phase_id="01_dossier",
                    name="Dossier",
                    required=False,
                    gate=GateSpec("dossier_ready"),
                ),
            ),
        )

        restored = DesignSpec.from_json(design.to_json())

        self.assertEqual(restored.design_id, "sc01-access")
        self.assertEqual(restored.phases[1].gate.gate_id, "dossier_ready")
        self.assertFalse(restored.phases[1].required)

    def test_design_rejects_unordered_phases(self) -> None:
        with self.assertRaises(ModelValidationError) as error:
            DesignSpec(
                design_id="bad-design",
                version="v1",
                title="Bad",
                target_model="ContractTarget",
                phases=(
                    PhaseSpec(phase_id="02_late", name="Late"),
                    PhaseSpec(phase_id="01_early", name="Early"),
                ),
            )

        self.assertEqual(error.exception.code, "unordered_phases")

    def test_run_options_roundtrip(self) -> None:
        options = RunOptions(resume=False, dry_run=True, metadata={"x": 1})

        restored = RunOptions.from_json(options.to_json())

        self.assertFalse(restored.resume)
        self.assertTrue(restored.dry_run)
        self.assertEqual(restored.metadata["x"], 1)


if __name__ == "__main__":
    unittest.main()
