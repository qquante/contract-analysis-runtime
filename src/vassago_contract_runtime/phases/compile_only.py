"""Phase 08 compile-only harness adapter."""

from __future__ import annotations

from vassago_contract_runtime.design_runtime.runner import PhaseContext, PhaseResult
from vassago_contract_runtime.foundry import FoundryAdapter, FoundryHarnessInput, NullFoundryAdapter
from vassago_contract_runtime.sc01_source import (
    contract_name_for_harness,
    render_initializer_call,
    should_use_uups_initializer_harness,
)


class CompileOnlyAdapter:
    """Generate a compile-only harness and invoke Foundry only when ready."""

    def __init__(self, foundry: FoundryAdapter | None = None) -> None:
        self.foundry = foundry or NullFoundryAdapter()

    def run(self, context: PhaseContext) -> PhaseResult:
        ready = _read_json(context, "07_proof_pieces", "sc01-runtime-ready.json")
        source_manifest = _read_json(context, "01_dossier", "source-manifest.json")
        harness = render_sc01_harness(source_manifest)
        compile_ready_count = int(ready.get("compile_ready_count") or 0)
        if compile_ready_count <= 0:
            result = {
                "status": "compile_skipped_not_ready",
                "target_id": context.target.target_id,
                "foundry_called": False,
                "provider": "not_invoked",
                "compile_ready_count": compile_ready_count,
                "runtime_ready_count": int(ready.get("runtime_ready_count") or 0),
                "evidence_status": "static_only",
                "blockers": list(ready.get("blockers") or ["compile_ready_count_zero"]),
            }
            return PhaseResult(
                json_artifacts={"compile-result.json": result},
                text_artifacts={"VassagoSC01Harness.t.sol": harness},
            )
        item = FoundryHarnessInput(
            target_id=context.target.target_id,
            harness_name="VassagoSC01Harness",
            source_files=dict(source_manifest.get("source_files") or {}),
            test_files={"VassagoSC01Harness.t.sol": harness},
            metadata={"compile_ready": True, "runtime_ready": False},
        )
        foundry_result = self.foundry.compile_harness(item)
        return PhaseResult(
            json_artifacts={
                "compile-result.json": {
                    "status": foundry_result.status,
                    "target_id": context.target.target_id,
                    "foundry_called": True,
                    "foundry": foundry_result.to_json(),
                    "evidence_status": "compile_only",
                }
            },
            text_artifacts={"VassagoSC01Harness.t.sol": harness},
        )


def _read_json(context: PhaseContext, phase_id: str, name: str) -> dict:
    uri = context.artifact_store.uri(context.target.target_id, phase_id, name)
    payload = context.artifact_store.read_artifact(uri)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON artifact for {phase_id}/{name}")
    return payload


def _sentinel_harness() -> str:
    return "\n".join(
        [
            "// SPDX-License-Identifier: MIT",
            "pragma solidity ^0.8.24;",
            "",
            "contract VassagoSC01Harness {",
            "    function __compileOnlySentinel() external pure returns (bool) {",
            "        return true;",
            "    }",
            "}",
            "",
        ]
    )


def render_sc01_harness(source_manifest: dict) -> str:
    if should_use_uups_initializer_harness(source_manifest):
        return _uups_initializer_harness(source_manifest)
    return _sentinel_harness()


def _uups_initializer_harness(source_manifest: dict) -> str:
    contract_name = contract_name_for_harness(source_manifest)
    init_call = render_initializer_call(source_manifest)
    return "\n".join(
        [
            "// SPDX-License-Identifier: MIT",
            "pragma solidity ^0.8.24;",
            "",
            f'import "../src/{contract_name}.sol";',
            "",
            "contract VassagoSC01Harness {",
            "    function testUnauthorizedCallerCanInitializeImplementation() external {",
            f"        {contract_name} target = new {contract_name}();",
            f"        {init_call}",
            "        require(target.owner() == address(this), \"owner not seized\");",
            "    }",
            "}",
            "",
        ]
    )
