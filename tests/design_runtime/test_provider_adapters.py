from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
from urllib.parse import parse_qs, urlparse
import tempfile
import unittest

from vassago_contract_runtime.contracts import ContractTargetRef, ExplorerSourceResolver
from vassago_contract_runtime.design_runtime.models import ContractTarget
from vassago_contract_runtime.explorer import EtherscanV2ExplorerAdapter, ExplorerContractContext, NullExplorerAdapter
from vassago_contract_runtime.foundry import FoundryHarnessInput, NullFoundryAdapter, SubprocessFoundryAdapter
from vassago_contract_runtime.slither import (
    NullSlitherAdapter,
    PythonSlitherAdapter,
    SlitherInput,
    SolcProvisionResult,
    SolcSelectManager,
    SubprocessSlitherAdapter,
)


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
        self.assertIn("Fixture.sol", first.source_files)
        self.assertIn("Fixture", " ".join(first.source_files.values()))

    def test_etherscan_v2_standard_json_normalizes_absolute_source_units(self) -> None:
        source_json = {
            "language": "Solidity",
            "sources": {
                "/Users/dev/project/contracts/v1/FiatTokenProxy.sol": {"content": "contract FiatTokenProxy {}"},
                "/Users/dev/project/contracts/upgradeability/AdminUpgradeabilityProxy.sol": {
                    "content": "contract AdminUpgradeabilityProxy {}"
                },
            },
        }

        def transport(url: str) -> dict:
            return {
                "status": "1",
                "message": "OK",
                "result": [
                    {
                        "ContractName": "FiatTokenProxy",
                        "CompilerVersion": "v0.6.12",
                        "ABI": "[]",
                        "SourceCode": json.dumps(source_json),
                        "Proxy": "0",
                        "Implementation": "",
                    }
                ],
            }

        target = ContractTargetRef.from_target(ContractTarget("base", "0x1111111111111111111111111111111111111111"))
        result = EtherscanV2ExplorerAdapter("test-key", min_interval_seconds=0, transport=transport).get_contract_context(target)

        self.assertEqual(result.status, "resolved")
        self.assertIn("v1/FiatTokenProxy.sol", result.source_files)
        self.assertIn("upgradeability/AdminUpgradeabilityProxy.sol", result.source_files)

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

    def test_explorer_source_resolver_maps_explorer_context_to_source_resolution(self) -> None:
        target = ContractTargetRef.from_target(ContractTarget("eth", "0x1111111111111111111111111111111111111111"))

        class FakeExplorer:
            def get_contract_context(self, requested: ContractTargetRef) -> ExplorerContractContext:
                self.requested = requested
                return ExplorerContractContext(
                    status="resolved",
                    provider="fake_explorer",
                    target=requested,
                    abi=[{"type": "function", "name": "owner", "inputs": [], "outputs": []}],
                    source_files={"Target.sol": "contract Target { address public owner; }"},
                    proxy_context={"proxy": "1", "implementation": "0ximpl"},
                    metadata={
                        "contract_name": "Target",
                        "compiler_version": "v0.8.20+commit.a1b79de6",
                        "evidence_status": "read_only_real",
                    },
                )

        explorer = FakeExplorer()
        resolution = ExplorerSourceResolver(explorer).resolve(target)

        self.assertEqual(explorer.requested, target)
        self.assertEqual(resolution.status, "resolved")
        self.assertEqual(resolution.provider, "fake_explorer")
        self.assertEqual(resolution.compiler["version"], "v0.8.20+commit.a1b79de6")
        self.assertEqual(resolution.proxy_context["implementation"], "0ximpl")
        self.assertEqual(resolution.metadata["source"], "explorer")
        self.assertEqual(resolution.metadata["evidence_status"], "read_only_real")

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

    def test_python_slither_adapter_normalizes_ir_with_fake_api(self) -> None:
        calls: list[dict[str, str]] = []

        class FakeVariable:
            def __init__(self, name: str) -> None:
                self.name = name

        class FakeSourceMapping:
            content = "function initialize() external onlyOwner { owner = msg.sender; }"
            start = 10
            length = 64
            lines = [3]
            filename = "Fixture.sol"

        class FakeNode:
            type = "IF"
            expression = "require(msg.sender == owner)"
            irs = ["owner := msg.sender"]

        class FakeFunction:
            name = "initialize"
            full_name = "initialize()"
            visibility = "external"
            state_mutability = "nonpayable"
            parameters = []
            modifiers = [FakeVariable("onlyOwner")]
            state_variables_written = [FakeVariable("owner"), FakeVariable("balances(address)")]
            state_variables_read = [FakeVariable("owner()")]
            variables_written = [FakeVariable("owner")]
            variables_read = [FakeVariable("msg.sender")]
            internal_calls = [FakeVariable("_authorizeUpgrade")]
            high_level_calls = []
            low_level_calls = []
            library_calls = []
            external_calls_as_expressions = []
            nodes = [FakeNode()]
            source_mapping = FakeSourceMapping()

        class FakeContract:
            name = "Fixture"
            inheritance = [FakeVariable("Ownable")]
            functions = [FakeFunction()]

        class FakeSlither:
            def __init__(self, target: str) -> None:
                self.target = target
                calls.append({"target": target, "cwd_name": Path.cwd().name, "solc_version": os.environ.get("SOLC_VERSION", "")})
                self.contracts = [FakeContract()]

        old_solc_version = os.environ.get("SOLC_VERSION")
        result = PythonSlitherAdapter(FakeSlither).analyze(
            SlitherInput(
                target_id="CT-test",
                source_files={"Fixture.sol": "contract Fixture {}"},
                compile_context={
                    "selected_source_file": "Fixture.sol",
                    "solc_version_selection": {"requested_version": "0.8.20", "source": "compiler_metadata"},
                },
                target_contract="Fixture",
            )
        )

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.provider, "slither_python")
        self.assertEqual(result.ir["status"], "completed")
        self.assertEqual(result.ir["functions"][0]["signature"], "initialize()")
        self.assertEqual(result.ir["functions"][0]["state_writes"], ["balances", "owner"])
        self.assertEqual(result.ir["functions"][0]["state_reads"], ["owner"])
        self.assertEqual(result.ir["functions"][0]["modifiers"], ["onlyOwner"])
        self.assertIn("owner := msg.sender", result.ir["functions"][0]["slithir_operations"])
        self.assertEqual(calls[0]["target"], "Fixture.sol")
        self.assertEqual(calls[0]["solc_version"], "0.8.20")
        self.assertEqual(os.environ.get("SOLC_VERSION"), old_solc_version)
        self.assertEqual(result.metadata["compiler_selection"]["requested_version"], "0.8.20")

    def test_solc_select_manager_reports_cache_missing_without_install(self) -> None:
        calls: list[list[str]] = []

        def runner(command: list[str], timeout_seconds: int) -> subprocess.CompletedProcess:
            calls.append(command)
            if command == ["solc-select", "versions"]:
                return subprocess.CompletedProcess(command, 0, stdout="0.8.20\n", stderr="")
            raise AssertionError(command)

        result = SolcSelectManager(runner=runner, current_version_getter=lambda: "0.8.20").prepare(
            "0.8.24",
            allow_install=False,
        )

        self.assertEqual(result.status, "compiler_cache_missing")
        self.assertEqual(result.requested_version, "0.8.24")
        self.assertEqual(result.installed_versions, ["0.8.20"])
        self.assertEqual(calls, [["solc-select", "versions"]])

    def test_solc_select_manager_installs_only_when_allowed(self) -> None:
        calls: list[list[str]] = []

        def runner(command: list[str], timeout_seconds: int) -> subprocess.CompletedProcess:
            calls.append(command)
            if command == ["solc-select", "versions"] and len(calls) == 1:
                return subprocess.CompletedProcess(command, 0, stdout="0.8.20\n", stderr="")
            if command == ["solc-select", "install", "0.8.24"]:
                return subprocess.CompletedProcess(command, 0, stdout="installed", stderr="")
            if command == ["solc-select", "versions"]:
                return subprocess.CompletedProcess(command, 0, stdout="0.8.20\n0.8.24\n", stderr="")
            raise AssertionError(command)

        result = SolcSelectManager(runner=runner, current_version_getter=lambda: "0.8.20").prepare(
            "0.8.24",
            allow_install=True,
        )

        self.assertEqual(result.status, "installed")
        self.assertEqual(result.requested_version, "0.8.24")
        self.assertTrue(result.install_attempted)
        self.assertEqual(calls[1], ["solc-select", "install", "0.8.24"])

    def test_python_slither_adapter_skips_when_requested_compiler_missing(self) -> None:
        class FakeManager:
            def prepare(self, requested_version: str, *, allow_install: bool = False) -> SolcProvisionResult:
                self.requested_version = requested_version
                self.allow_install = allow_install
                return SolcProvisionResult(
                    status="compiler_cache_missing",
                    requested_version=requested_version,
                    current_solc_version="0.8.20",
                    installed_versions=["0.8.20"],
                    manager="fake",
                )

        class ShouldNotRun:
            def __init__(self, target: str) -> None:
                raise AssertionError("Slither should not run when compiler cache is missing.")

        manager = FakeManager()
        result = PythonSlitherAdapter(ShouldNotRun, solc_manager=manager).analyze(
            SlitherInput(
                target_id="CT-test",
                source_files={"Fixture.sol": "contract Fixture {}"},
                compile_context={
                    "selected_source_file": "Fixture.sol",
                    "solc_version_selection": {"requested_version": "0.8.24", "source": "compiler_metadata"},
                },
            )
        )

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.error["code"], "solc_version_cache_missing")
        self.assertEqual(result.metadata["compiler_selection"]["provisioning"]["status"], "compiler_cache_missing")
        self.assertEqual(manager.requested_version, "0.8.24")
        self.assertEqual(manager.allow_install, False)

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
        serialized = result.to_json()
        self.assertIn("<redacted-rpc-url>", serialized["command"])
        self.assertNotIn("http://127.0.0.1:8545", serialized["command"])


if __name__ == "__main__":
    unittest.main()
