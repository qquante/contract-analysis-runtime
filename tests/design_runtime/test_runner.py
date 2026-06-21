from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from vassago_contract_runtime.design_runtime.manifest import phase_status
from vassago_contract_runtime.design_runtime.models import ContractTarget, DesignSpec, PhaseSpec, PhaseStatus, RunOptions
from vassago_contract_runtime.design_runtime.runner import PhaseContext, PhaseResult, run_design


class RecordingAdapter:
    def __init__(self, calls: list[str], status: PhaseStatus = PhaseStatus.COMPLETED) -> None:
        self.calls = calls
        self.status = status

    def run(self, context: PhaseContext) -> PhaseResult:
        self.calls.append(context.phase.phase_id)
        if self.status == PhaseStatus.FAILED:
            return PhaseResult.failed("planned_failure", "planned failure")
        return PhaseResult.completed(json_artifacts={f"{context.phase.phase_id}.json": {"phase": context.phase.phase_id}})


def target() -> ContractTarget:
    return ContractTarget("base", "0x2222222222222222222222222222222222222222")


def design(required_second: bool = True) -> DesignSpec:
    return DesignSpec(
        design_id="sc01-access",
        version="v0.1.0",
        title="SC01",
        target_model="ContractTarget",
        phases=(
            PhaseSpec("00_intake", "Intake"),
            PhaseSpec("01_dossier", "Dossier", required=required_second),
            PhaseSpec("02_semantic_surface", "Surface"),
        ),
    )


class RunnerTests(unittest.TestCase):
    def test_run_design_runs_all_phases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            calls: list[str] = []
            d = design()
            adapters = {phase.phase_id: RecordingAdapter(calls) for phase in d.phases}

            result = run_design(d, [target()], Path(tmp) / "run", adapters)

            self.assertEqual(result.status, "completed")
            self.assertEqual(calls, ["00_intake", "01_dossier", "02_semantic_surface"])
            self.assertEqual(result.executed_count, 3)

    def test_resume_skips_completed_phases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            d = design()
            calls_first: list[str] = []
            adapters_first = {
                "00_intake": RecordingAdapter(calls_first),
                "01_dossier": RecordingAdapter(calls_first, status=PhaseStatus.FAILED),
                "02_semantic_surface": RecordingAdapter(calls_first),
            }
            first = run_design(d, [target()], run_dir, adapters_first)
            self.assertEqual(first.status, "stopped")

            calls_second: list[str] = []
            adapters_second = {phase.phase_id: RecordingAdapter(calls_second) for phase in d.phases}
            second = run_design(d, [target()], run_dir, adapters_second, RunOptions(resume=True))

            self.assertEqual(calls_second, ["01_dossier", "02_semantic_surface"])
            self.assertGreaterEqual(second.skipped_count, 1)
            self.assertEqual(phase_status(run_dir, target().target_id, "02_semantic_surface"), PhaseStatus.COMPLETED)

    def test_required_failure_skips_later_phase(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = design()
            calls: list[str] = []
            adapters = {
                "00_intake": RecordingAdapter(calls),
                "01_dossier": RecordingAdapter(calls, status=PhaseStatus.FAILED),
                "02_semantic_surface": RecordingAdapter(calls),
            }

            result = run_design(d, [target()], Path(tmp) / "run", adapters)

            self.assertEqual(result.status, "stopped")
            self.assertEqual(calls, ["00_intake", "01_dossier"])
            self.assertEqual(result.failed_count, 1)

    def test_optional_failure_can_continue(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = design(required_second=False)
            calls: list[str] = []
            adapters = {
                "00_intake": RecordingAdapter(calls),
                "01_dossier": RecordingAdapter(calls, status=PhaseStatus.FAILED),
                "02_semantic_surface": RecordingAdapter(calls),
            }

            result = run_design(d, [target()], Path(tmp) / "run", adapters)

            self.assertEqual(result.status, "completed_with_failures")
            self.assertEqual(calls, ["00_intake", "01_dossier", "02_semantic_surface"])
            self.assertEqual(result.failed_count, 1)


if __name__ == "__main__":
    unittest.main()
