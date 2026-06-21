from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs, urlparse
import tempfile
import unittest

from vassago_contract_runtime.contracts import ContractTargetRef
from vassago_contract_runtime.design_runtime.models import ContractTarget
from vassago_contract_runtime.explorer import EtherscanV2ExplorerAdapter, NullExplorerAdapter
from vassago_contract_runtime.slither import NullSlitherAdapter, SlitherInput


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


if __name__ == "__main__":
    unittest.main()
