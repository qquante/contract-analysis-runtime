from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from vassago_contract_runtime.artifacts.store import ArtifactStore, ArtifactStoreError, stable_json_hash
from vassago_contract_runtime.design_runtime.manifest import (
    create_run_manifest,
    load_run_manifest,
    phase_status,
    update_phase_status,
)
from vassago_contract_runtime.design_runtime.models import (
    ArtifactSpec,
    ContractTarget,
    DesignSpec,
    PhaseSpec,
    PhaseStatus,
)


def sample_design() -> DesignSpec:
    return DesignSpec(
        design_id="sc01-access",
        version="v0.1.0",
        title="SC01",
        target_model="ContractTarget",
        phases=(
            PhaseSpec("00_intake", "Intake", outputs=(ArtifactSpec("target-manifest.json"),)),
            PhaseSpec("01_dossier", "Dossier", outputs=(ArtifactSpec("scan-dossier.json"),)),
        ),
    )


def sample_target() -> ContractTarget:
    return ContractTarget("eth", "0x1111111111111111111111111111111111111111")


class ManifestTests(unittest.TestCase):
    def test_create_and_load_run_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            manifest = create_run_manifest(run_dir, sample_design(), [sample_target()], run_id="RUN-test")

            loaded = load_run_manifest(run_dir)

            self.assertEqual(manifest["run_id"], "RUN-test")
            self.assertEqual(loaded["summary"]["target_count"], 1)
            self.assertTrue((run_dir / "targets" / sample_target().target_id / "target-manifest.json").is_file())

    def test_update_phase_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            design = sample_design()
            target = sample_target()
            create_run_manifest(run_dir, design, [target], run_id="RUN-test")

            update_phase_status(run_dir, target.target_id, design.phases[0], PhaseStatus.COMPLETED)

            self.assertEqual(phase_status(run_dir, target.target_id, "00_intake"), PhaseStatus.COMPLETED)

    def test_artifact_store_roundtrip_and_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            design = sample_design()
            target = sample_target()
            create_run_manifest(run_dir, design, [target], run_id="RUN-test")
            store = ArtifactStore(run_dir, "RUN-test")

            ref = store.write_json_artifact(target.target_id, "00_intake", "target-manifest.json", {"ok": True})

            self.assertEqual(store.read_artifact(ref["uri"]), {"ok": True})
            self.assertEqual(stable_json_hash({"ok": True}), stable_json_hash({"ok": True}))
            self.assertEqual(len(ref["sha256"]), 64)

    def test_artifact_store_blocks_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ArtifactStore(Path(tmp), "RUN-test")

            with self.assertRaises(ArtifactStoreError):
                store.write_text_artifact("CT-test", "00_intake", "../escape.txt", "bad")

            with self.assertRaises(ArtifactStoreError):
                store.read_artifact("vassago://runs/RUN-test/targets/CT-test/phases/00_intake/../escape.txt")


if __name__ == "__main__":
    unittest.main()
