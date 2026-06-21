from __future__ import annotations

from pathlib import Path
import subprocess
from urllib.parse import parse_qs, urlparse
import tempfile
import unittest

from vassago_contract_runtime.contracts import ContractTargetRef
from vassago_contract_runtime.design_runtime.models import ContractTarget
from vassago_contract_runtime.explorer import EtherscanV2ExplorerAdapter, NullExplorerAdapter
from vassago_contract_runtime.foundry import FoundryHarnessInput, NullFoundryAdapter, SubprocessFoundryAdapter
from vassago_contract_runtime.slither import NullSlitherAdapter, SlitherInput, SubprocessSlitherAdapter


class ProviderAdapterTests(unittest.TestCase):
    def test_null_explorer_is_unresolved_and_offline(self) -> None:
        target = ContractTargetRef.from_target(ContractTarget("eth", "0x1111111111111111111111111111111111111111"))

        result = NullExplorerAdapter().get_contract_context(target)

        self.assertEqual(result.status, "unresolved")
        self.assertEqual(result.provider, "null")
        self.assertEqual(result.error["code"], "explorer_adapter_not_configured")

    def test_etherscan_v2_contract_context_uses_chainid_and_cache(self) -> None:
        calls: list[str] = []

        def transport(url: str) -> dict:
            calls.append(url)
            params = parse_qs(urlparse(url).query)
            self.assertEqual(params["chainid"], ["8453"])
            self.assertNotIn("api_key", url)
            return {
                "status": "1",
                "message": "OK",
                "result": [
                    {
                        "ContractName": "Fixture",
                        "CompilerVersion": "v0.8.24",
                        "ABI": '[{"type":"function","name":"initialize","inputs":[],"outputs":[]}]',
                        "SourceCode": "contract Fixture { function initialize() external {} }",
                        "Proxy": "0",
                        "Implementation": "",
                    }
                ],
            }

        target = ContractTargetRef.from_target(ContractTarget("base", "0x1111111111111111111111111111111111111111"))
        with tempfile.TemporaryDirectory() as tmp:
            adapter = EtherscanV2ExplorerAdapter(
                "test-key",
                cache_dir=Path(tmp),
                min_interval_seconds=0,
                transport=transport,
            )

            first = adapter.get_contract_context(target)
            second = adapter.get_contract_context(target)

        self.assertEqual(first.status, "resolved")
        self.assertEqual(second.status, "resolved")
        self.assertEqual(first.metadata["cache_hit"], False)
        self.assertEqual(second.metadata["cache_hit"], True)
        self.assertEqual(len(calls), 1)
        self.assertEqual(first.abi[0]["name"], "initialize")
        self.assertIn("Fixture", " ".join(first.source_files.values()))

    def test_etherscan_v2_logs_are_read_only_and_structured(self) -> None:
        def transport(url: str) -> dict:
            params = parse_qs(urlparse(url).query)
            self.assertEqual(params["module"], ["logs"])
            self.assertEqual(params["action"], ["getLogs"])
            return {
                "status": "1",
                "message": "OK",
                "result": [{"blockNumber": "0x1", "topics": ["0xabc"], "data": "0x"}],
            }

        target = ContractTargetRef.from_target(ContractTarget("eth", "0x1111111111111111111111111111111111111111"))
        result = EtherscanV2ExplorerAdapter("test-key", min_interval_seconds=0, transport=transport).get_logs(
            target,
            from_block=1,
            to_block=2,
        )

        self.assertEqual(result.status, "resolved")
        self.assertEqual(result.to_json()["log_count"], 1)
        self.assertEqual(result.metadata["evidence_status"], "read_only_real")

    def test_null_slither_adapter_is_unavailable(self) -> None:
        result = NullSlitherAdapter().analyze(SlitherInput(target_id="CT-test", source_files={}))

        self.assertEqual(result.status, "unavailable")
        self.assertEqual(result.provider, "null")
        self.assertEqual(result.error["code"], "slither_adapter_not_configured")

    def test_subprocess_slither_adapter_parses_json_output_with_fake_runner(self) -> None:
        def runner(command: list[str], cwd: Path, timeout_seconds: int) -> subprocess.CompletedProcess:
            self.assertEqual(command[0], "slither")
            self.assertEqual(timeout_seconds, 120)
            output = Path(command[-1])
            output.write_text(
                '{"success": true, "error": null, "results": {"detectors": [{"check": "protected-vars"}]}}',
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

        result = SubprocessSlitherAdapter(runner=runner).analyze(
            SlitherInput(
                target_id="CT-test",
                source_files={"Fixture.sol": "contract Fixture {}"},
                compile_context={"selected_source_file": "Fixture.sol"},
            )
        )

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.provider, "slither_subprocess")
        self.assertEqual(result.detectors[0]["check"], "protected-vars")

    def test_subprocess_slither_missing_binary_is_unavailable(self) -> None:
        def runner(command: list[str], cwd: Path, timeout_seconds: int) -> subprocess.CompletedProcess:
            raise FileNotFoundError(command[0])

        result = SubprocessSlitherAdapter(runner=runner).analyze(
            SlitherInput(target_id="CT-test", source_files={"Fixture.sol": "contract Fixture {}"})
        )

        self.assertEqual(result.status, "unavailable")
        self.assertEqual(result.error["code"], "slither_executable_not_found")

    def test_null_foundry_adapter_blocks_compile_and_runtime(self) -> None:
        item = FoundryHarnessInput(target_id="CT-test", harness_name="Harness", source_files={}, test_files={})
        adapter = NullFoundryAdapter()

        compile_result = adapter.compile_harness(item)
        runtime_result = adapter.run_local_fork(item)

        self.assertEqual(compile_result.status, "unavailable")
        self.assertEqual(runtime_result.status, "blocked")
        self.assertEqual(runtime_result.error["code"], "foundry_runtime_not_configured")

    def test_subprocess_foundry_compile_uses_forge_build_with_ephemeral_workspace(self) -> None:
        commands: list[list[str]] = []

        def runner(command: list[str], cwd: Path, timeout_seconds: int) -> subprocess.CompletedProcess:
            commands.append(command)
            self.assertTrue((cwd / "foundry.toml").is_file())
            self.assertTrue((cwd / "test" / "Harness.t.sol").is_file())
            self.assertEqual(timeout_seconds, 33)
            return subprocess.CompletedProcess(command, 0, stdout="compiled", stderr="")

        item = FoundryHarnessInput(
            target_id="CT-test",
            harness_name="Harness",
            source_files={"Target.sol": "contract Target {}"},
            test_files={"Harness.t.sol": "contract Harness {}"},
        )

        result = SubprocessFoundryAdapter(timeout_seconds=33, runner=runner).compile_harness(item)

        self.assertEqual(commands, [["forge", "build"]])
        self.assertEqual(result.status, "compile_only_passed")
        self.assertEqual(result.metadata["evidence_status"], "compile_only")
        self.assertEqual(result.metadata["no_broadcast_command"], True)

    def test_subprocess_foundry_runtime_requires_explicit_gate(self) -> None:
        item = FoundryHarnessInput(target_id="CT-test", harness_name="Harness", source_files={}, test_files={})

        result = SubprocessFoundryAdapter(runner=lambda *_: None).run_local_fork(item)

        self.assertEqual(result.status, "blocked")
        self.assertEqual(result.error["code"], "foundry_runtime_gate_not_satisfied")

    def test_subprocess_foundry_runtime_uses_forge_test_when_authorized(self) -> None:
        commands: list[list[str]] = []

        def runner(command: list[str], cwd: Path, timeout_seconds: int) -> subprocess.CompletedProcess:
            commands.append(command)
            self.assertTrue((cwd / "test" / "Harness.t.sol").is_file())
            return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

        item = FoundryHarnessInput(
            target_id="CT-test",
            harness_name="Harness",
            source_files={},
            test_files={"Harness.t.sol": "contract Harness {}"},
            fork={"rpc_url": "http://127.0.0.1:8545", "block_number": 123},
            metadata={"runtime_ready": True, "runtime_authorized": True},
        )

        result = SubprocessFoundryAdapter(runner=runner).run_local_fork(item)

        self.assertEqual(result.status, "runtime_completed")
        self.assertEqual(commands[0][:4], ["forge", "test", "--match-contract", "Harness"])
        self.assertIn("--fork-url", commands[0])
        self.assertIn("--fork-block-number", commands[0])
        self.assertEqual(result.metadata["no_broadcast_command"], True)


if __name__ == "__main__":
    unittest.main()
