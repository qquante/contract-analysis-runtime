# Sessions

## S-20260621-001 - Repository bootstrap

Goal:

- Create a clean repository for contract-first campaign runtime.

What was done:

- Created `C:\Users\PC\Desktop\vassago-contract-runtime`.
- Added initial docs and directory layout.
- Defined the core decision: contract-first, repo-mode secondary.
- Defined SC01 as the first Design.

Decisions:

- Do not throw away original Vassago.
- Do not copy all old tools into this repo.
- Build a deep Design Runtime first.
- Keep Foundry as a local runtime phase, not an ad hoc manual exception.

Reasoning:

- The old Vassago has many working pieces but too much top-level tool surface.
- DLT Auditor is operationally better because it has designs, phases, manifests,
  isolation and resume.
- This repo should copy that execution discipline, not its exact domain.

Blockers:

- No implementation yet.
- No real adapters yet.
- No CLI yet.

Next:

- Implement PT-023.T01-T03.

## S-20260621-002 - PT-023.T01-T03 runtime foundation

Goal:

- Implement the first runtime foundation slices: models, manifests, artifact store
  and phase runner with resume.

What was done:

- Added `src/vassago_contract_runtime/design_runtime/models.py`.
- Added `src/vassago_contract_runtime/design_runtime/manifest.py`.
- Added `src/vassago_contract_runtime/design_runtime/runner.py`.
- Added `src/vassago_contract_runtime/artifacts/store.py`.
- Added 14 unit tests under `tests/design_runtime/`.

Decisions:

- `ContractTarget` is normalized to lowercase chain/address.
- Target ids use `CT-<short_hash(chain|address)>`.
- Phase ids must use the stable format `NN_slug`.
- Artifact URIs use
  `vassago://runs/{run_id}/targets/{target_id}/phases/{phase_id}/{artifact}`.
- `ArtifactStore` owns artifact validation errors, even when the lower-level
  model validator catches the bad name first.

Reasoning:

- The runtime needs a small Interface before any old Vassago adapter is ported.
- Fake phase adapters are enough to prove resume/manifest semantics first.

Validation:

- `$env:PYTHONPATH='src'; python -m unittest discover -s tests` passed:
  14 tests.

Blockers:

- No CLI yet.
- No design YAML loader yet.
- No real phase adapters yet.

Next:

- Implement `PT-023.T04` CLI skeleton.
- Implement `PT-023.T05` strict check.
- Implement `PT-024.T01` design spec validation.

## S-20260621-003 - CLI, check and SC01 design validation

Goal:

- Implement `PT-023.T04`, `PT-023.T05` and `PT-024.T01`.

What was done:

- Added `src/vassago_contract_runtime/design_runtime/design_loader.py`.
- Added `src/vassago_contract_runtime/design_runtime/adapters.py`.
- Added `src/vassago_contract_runtime/cli.py`.
- Added `src/vassago_contract_runtime/quality.py`.
- Added `tests/design_runtime/test_design_loader.py`.
- Added `tests/design_runtime/test_cli.py`.
- Added `tests/fixtures/targets.json`.

Decisions:

- Use a controlled simple YAML parser for the current `design.yaml` subset
  instead of adding PyYAML immediately.
- Keep `run-design` limited to `--dry-run` until real phase adapters exist.
- `check` validates design load, line limit, evidence string placement, secret
  patterns and artifact path traversal behavior.
- Dry-run adapters write explicit `status=dry_run` artifacts, never evidence.

Validation:

- `$env:PYTHONPATH='src'; python -m unittest discover -s tests` passed:
  21 tests.
- `python -m vassago_contract_runtime.cli check` passed.
- `python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets.json --output <temp> --dry-run` passed.
- `python -m vassago_contract_runtime.cli resume --run <temp> --dry-run` passed and skipped completed phases.
- `python -m vassago_contract_runtime.cli artifact-read --run <temp> --uri <artifact-uri>` passed.

Blockers:

- No real phase adapters yet.
- No SourceResolver/Explorer/Slither/Foundry adapters yet.

Next:

- Implement `PT-024.T02` phase 00 intake as a real adapter.
- Implement `PT-024.T03` phase 01 dossier skeleton.

## S-20260621-004 - Intake, dossier skeleton and SourceResolver interface

Goal:

- Implement `PT-024.T02`, `PT-024.T03` and `PT-025.T01`.

What was done:

- Added `src/vassago_contract_runtime/contracts/target.py`.
- Added `src/vassago_contract_runtime/contracts/source_resolver.py`.
- Added `src/vassago_contract_runtime/phases/intake.py`.
- Added `src/vassago_contract_runtime/phases/dossier.py`.
- Updated CLI bootstrap mode to run real phase 00/01 adapters and dry-run the
  remaining phases.
- Added `tests/design_runtime/test_phases.py`.

Decisions:

- `NullSourceResolver` is explicit: status `unresolved`, provider `null`,
  no network.
- Phase 01 dossier is a skeleton until SourceResolver providers exist.
- `--bootstrap-adapters` means phase 00/01 are real local adapters and later
  phases remain dry-run.

Validation:

- `$env:PYTHONPATH='src'; python -m unittest discover -s tests` passed:
  24 tests.

Blockers:

- No Etherscan/Sourcify/local fixture SourceResolver adapter yet.
- No Explorer Adapter yet.
- No Corpus Adapter yet.

Next:

- Implement `PT-025.T05` Corpus Adapter interface.
- Implement `PT-024.T05` corpus motifs skeleton.
- Implement local fixture SourceResolver before network providers.

## S-20260621-005 - Corpus motifs, Explorer interface and fixture source

Goal:

- Implement `PT-025.T05`, `PT-024.T05`, `PT-025.T02` and fixture/local
  SourceResolver support for `PT-024.T03B`.

What was done:

- Added `FixtureSourceResolver` to
  `src/vassago_contract_runtime/contracts/source_resolver.py`.
- Added `src/vassago_contract_runtime/explorer/adapter.py` with
  `ExplorerAdapter`, `ExplorerContractContext` and `NullExplorerAdapter`.
- Added `src/vassago_contract_runtime/corpus/adapter.py` with
  `CorpusAdapter`, `CorpusScanContext`, `CorpusScanResult`,
  `DesignCorpusAdapter` and `NullCorpusAdapter`.
- Added `src/vassago_contract_runtime/phases/corpus_motifs.py`.
- Updated `src/vassago_contract_runtime/cli.py`:
  - `run-design --source-fixture <json>`;
  - `resume --source-fixture <json>`;
  - `--bootstrap-adapters` now runs real local phases 00, 01 and 03.
- Added `tests/fixtures/source_fixture.json`.
- Updated `designs/sc01-access/design.yaml` so phase 01 declares
  `protocol-fingerprint.json`.

Decisions:

- `FixtureSourceResolver` is filesystem-only and local. It does not call
  Etherscan, Sourcify, RPC or any network provider.
- Corpus motif hits are thesis routing hints only. They write
  `candidate_only`/`no_matches`, never proof or reproduced evidence.
- Explorer is only an interface in this slice. Real provider/cache/rate-limit
  implementation is future `PT-025.T02B`.
- Phase 02 remains dry-run in bootstrap mode; phase 03 can still use phase 01
  ABI/source to create local corpus candidates.

Validation:

- `$env:PYTHONPATH='src'; python -m unittest tests.design_runtime.test_phases`
  passed: 5 tests.
- `$env:PYTHONPATH='src'; python -m vassago_contract_runtime.cli check`
  passed.

Blockers:

- No real Explorer provider/cache adapter yet.
- No phase 02 semantic surface adapter yet.
- No Slither adapter yet.
- No thesis acquisition/source-truth/proof-piece adapters yet.

Next:

- Implement `PT-024.T04` semantic surface skeleton.
- Implement `PT-024.T06` thesis acquisition skeleton.
- Implement `PT-025.T02B` read-only Explorer provider/cache adapter.
- Implement `PT-025.T03` Slither Adapter interface.

## S-20260621-006 - Semantic surface, thesis acquisition, Explorer cache and Slither interface

Goal:

- Implement `PT-024.T04`, `PT-024.T06`, `PT-025.T02B` and `PT-025.T03`.

What was done:

- Added `src/vassago_contract_runtime/phases/semantic_surface.py`.
- Added `src/vassago_contract_runtime/phases/thesis_acquisition.py`.
- Extended `src/vassago_contract_runtime/explorer/adapter.py` with:
  - `ExplorerLogsResult`;
  - `EtherscanV2ExplorerAdapter`;
  - read-only `get_contract_context`;
  - read-only `get_logs`;
  - filesystem cache with API key excluded from cache key.
- Added `src/vassago_contract_runtime/slither/adapter.py`.
- Updated `src/vassago_contract_runtime/cli.py` so `--bootstrap-adapters`
  runs real local phases 00, 01, 02, 03 and 04.
- Added `tests/design_runtime/test_provider_adapters.py`.
- Updated phase tests so bootstrap fixture now verifies semantic surface,
  corpus candidates and thesis queue.

Decisions:

- Phase 02 is a semantic skeleton, not source truth. It writes static/candidate
  sidecars only.
- Phase 04 only ranks/routs thesis candidates to `05_source_truth`.
- Etherscan V2 is implemented as a read-only provider using the documented
  `chainid` parameter and `contract/getsourcecode`, `contract/getabi`,
  `logs/getLogs` actions.
- Slither is only an interface/null adapter in this slice. Real Slither
  execution stays behind future `PT-025.T03B`.

Validation:

- `$env:PYTHONPATH='src'; python -m unittest discover -s tests` passed:
  30 tests.
- `$env:PYTHONPATH='src'; python -m vassago_contract_runtime.cli check`
  passed.
- `$env:PYTHONPATH='src'; python -m compileall -q src` passed.

Smoke:

- `python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets.json --source-fixture tests/fixtures/source_fixture.json --output <temp> --bootstrap-adapters`
  passed.
- Result summary:
  - `status=completed`;
  - `failed_count=0`;
  - `candidate_status=candidate_only`;
  - `candidate_count=2`;
  - thesis ids: `uninitialized_implementation_proxy,uups_weak_auth`.

Blockers:

- Phase 05 source truth does not exist yet.
- Phase 06 on-chain state does not exist yet.
- Real Slither execution does not exist yet.
- Foundry adapter/interface still pending.

Next:

- Implement `PT-024.T07` source truth skeleton.
- Implement `PT-024.T08` on-chain state skeleton.
- Implement `PT-025.T04` Foundry Adapter interface.
- Implement `PT-025.T03B` real Slither subprocess/Python API adapter.

## S-20260621-007 - Source truth, on-chain state, Foundry interface and Slither subprocess

Goal:

- Implement `PT-024.T07`, `PT-024.T08`, `PT-025.T04` and `PT-025.T03B`.

What was done:

- Added `src/vassago_contract_runtime/phases/source_truth.py`.
- Added `src/vassago_contract_runtime/phases/onchain_state.py`.
- Added `src/vassago_contract_runtime/foundry/adapter.py`.
- Extended `src/vassago_contract_runtime/slither/adapter.py` with
  `SubprocessSlitherAdapter`.
- Updated `src/vassago_contract_runtime/cli.py` so `--bootstrap-adapters`
  runs real local phases 00 through 06.
- Updated `tests/design_runtime/test_phases.py`.
- Updated `tests/design_runtime/test_provider_adapters.py`.

Decisions:

- Source truth skeleton writes `source_truth_verified=false` for every queued
  candidate. It is a blocking review sidecar, not a proof engine.
- On-chain state skeleton writes `needs_provider` sidecars and makes no RPC
  calls in bootstrap mode.
- Foundry now has an interface/null adapter only. Real `forge` execution remains
  future work.
- Slither subprocess adapter is real but opt-in. Bootstrap mode does not call
  Slither automatically.
- Slither subprocess uses the documented CLI JSON path:
  `slither <source> --json <file>`.

Validation:

- `$env:PYTHONPATH='src'; python -m unittest tests.design_runtime.test_phases tests.design_runtime.test_provider_adapters`
  passed: 12 tests.
- `$env:PYTHONPATH='src'; python -m vassago_contract_runtime.cli check`
  passed.

Blockers:

- Phase 07 proof pieces does not exist yet.
- Phase 08 compile-only skeleton does not exist yet.
- Phase 10 final report skeleton does not exist yet.
- Real Foundry subprocess adapter is still pending.
- Real RPC state reader is still pending.

Next:

- Implement `PT-024.T09` proof pieces skeleton.
- Implement `PT-024.T10` compile-only skeleton.
- Implement `PT-024.T12` final report skeleton.
- Implement `PT-025.T04B` real Foundry subprocess adapter.

## S-20260621-008 - Proof pieces, compile-only, final report and Foundry subprocess

Goal:

- Implement `PT-024.T09`, `PT-024.T10`, `PT-024.T12` and `PT-025.T04B`.

What was done:

- Added `src/vassago_contract_runtime/phases/proof_pieces.py`.
- Added `src/vassago_contract_runtime/phases/compile_only.py`.
- Added `src/vassago_contract_runtime/phases/final_report.py`.
- Extended `src/vassago_contract_runtime/foundry/adapter.py` with `SubprocessFoundryAdapter`.
- Exported `SubprocessFoundryAdapter` from `src/vassago_contract_runtime/foundry/__init__.py`.
- Updated `src/vassago_contract_runtime/cli.py` so `--bootstrap-adapters` runs real local phases 00 through 08 and phase 10.
- Updated provider and phase tests for Foundry compile/runtime gating.

Decisions:

- Phase 07 is the canonical proof-piece gate. It writes `foundry_allowed=false` until source truth, actor model, codable args, reader, delta and predicate are complete.
- Phase 08 writes a harmless sentinel harness but skips Foundry when `compile_ready_count=0`.
- `SubprocessFoundryAdapter.compile_harness()` runs `forge build` in an ephemeral workspace.
- `SubprocessFoundryAdapter.run_local_fork()` can run `forge test`, but only with explicit `runtime_ready=true` and `runtime_authorized=true` metadata.
- Phase 10 reports `blocked_no_runtime_ready` for the current fixture bootstrap. It does not promote evidence.

Validation:

- `$env:PYTHONPATH='src'; python -m unittest tests.design_runtime.test_phases tests.design_runtime.test_provider_adapters` passed: 15 tests.
- `$env:PYTHONPATH='src'; python -m unittest discover -s tests` passed: 36 tests.
- `$env:PYTHONPATH='src'; python -m vassago_contract_runtime.cli check` passed.
- `$env:PYTHONPATH='src'; python -m compileall -q src` passed.
- Smoke command passed:
  `python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets.json --source-fixture tests/fixtures/source_fixture.json --output <temp> --bootstrap-adapters`.
- Smoke result: `status=completed`, `failed_count=0`, `runtime_ready_count=0`, `foundry_allowed=false`, `compile_status=compile_skipped_not_ready`, `foundry_called=false`, `final_status=blocked_no_runtime_ready`.

Blockers:

- Phase 09 runtime Foundry is still dry-run in bootstrap mode.
- There is no positive fixture yet that produces `compile_ready_count>0`.
- No RPC/provider state reader is wired into on-chain state.

Next:

- Implement `PT-024.T11` runtime Foundry local phase only behind `foundry_allowed=true`.
- Implement `PT-026.T01` tool contracts for run/resume/artifact-read.
- Add a fixture that intentionally reaches compile-ready for phase 08 positive coverage.

RESUME FROM HERE:

Start with `PT-024.T11` only if a runtime-ready gate exists, otherwise implement `PT-026.T01` tool contracts. Use `run-design --bootstrap-adapters` as the smoke command. Do not run Foundry runtime unless `sc01-runtime-ready.json` has `foundry_allowed=true` and the caller passes explicit local authorization. Current tests are 36 OK and `check` passes.

## S-20260621-009 - Agent tool contracts for design runtime

Goal:

- Implement `PT-026.T01` tool contracts for `run_design`, `resume_design` and `artifact_read`.

What was done:

- Added `src/vassago_contract_runtime/runtime_api.py` as the shared programmatic API used by CLI and tools.
- Added `src/vassago_contract_runtime/tools/contracts.py` with `ToolContract`, `ToolInvocation`, `ToolRunResult` and `ToolRegistry`.
- Added `src/vassago_contract_runtime/tools/runtime_tools.py` with contracts for:
  - `vassago_design_run`;
  - `vassago_design_resume`;
  - `vassago_artifact_read`.
- Added `src/vassago_contract_runtime/tools/__init__.py` exports.
- Updated `src/vassago_contract_runtime/cli.py` to call `runtime_api.py` instead of carrying its own duplicate run/resume/artifact logic.
- Added `tests/design_runtime/test_tool_contracts.py`.

Decisions:

- Tool contracts are campaign-level only. The top-level agent should not receive phase-level builder tools yet.
- Tool policy is local-only, no-shell, no-broadcast and no private keys.
- MCP stdio should wrap this registry in `PT-026.T02`; it should not reimplement run/resume/read behavior.

Validation:

- `$env:PYTHONPATH='src'; python -m unittest tests.design_runtime.test_tool_contracts` passed: 4 tests.
- `$env:PYTHONPATH='src'; python -m unittest discover -s tests` passed: 40 tests.
- `$env:PYTHONPATH='src'; python -m vassago_contract_runtime.cli check` passed.

Blockers:

- No MCP stdio server exists yet.
- No positive compile-ready fixture exists yet.
- Phase 09 runtime Foundry remains dry-run unless a runtime-ready report and explicit authorization exist.

Next:

- Implement `PT-026.T02` MCP stdio local over `build_runtime_tool_registry()`.
- Add a compile-ready fixture to exercise phase 08 positive path.
- Implement `PT-024.T11` only behind `foundry_allowed=true`.

RESUME FROM HERE:

Start with `PT-026.T02` MCP stdio local. Reuse `build_runtime_tool_registry()` and expose only `vassago_design_run`, `vassago_design_resume` and `vassago_artifact_read`. Keep the MCP server local-only, no shell and no broadcast. Current tests are 40 OK and `check` passes before final validation.

## S-20260621-010 - MCP stdio local over runtime tool contracts

Goal:

- Implement `PT-026.T02` MCP stdio local over `build_runtime_tool_registry()`.

What was done:

- Added `src/vassago_contract_runtime/mcp/server.py`.
- Added `src/vassago_contract_runtime/mcp/__init__.py`.
- Added CLI command: `python -m vassago_contract_runtime.cli mcp --stdio`.
- Added `tests/design_runtime/test_mcp_server.py`.
- Updated docs/control files for PT-026.T02.

Decisions:

- MCP stdio wraps only the campaign-level registry from `build_runtime_tool_registry()`.
- Exposed methods are intentionally small: `initialize`, `notifications/initialized`, `ping`, `tools/list` and `tools/call`.
- No shell, no broadcast and no fine-grained phase tools are exposed.
- The implementation is dependency-free and speaks newline-delimited JSON-RPC over stdio.

Validation:

- `$env:PYTHONPATH='src'; python -m unittest tests.design_runtime.test_mcp_server` passed: 6 tests.
- `$env:PYTHONPATH='src'; python -m unittest discover -s tests` passed: 46 tests.
- `$env:PYTHONPATH='src'; python -m vassago_contract_runtime.cli check` passed.
- CLI stdio smoke passed:
  `initialize` returned tools capability and `tools/list` returned exactly `vassago_design_run`, `vassago_design_resume` and `vassago_artifact_read`.

Blockers:

- Hermes skill `vassago-sc01-design` does not exist yet.
- No positive compile-ready fixture exists yet.
- Phase 09 runtime Foundry remains dry-run unless a runtime-ready report and explicit authorization exist.

Next:

- Implement `PT-026.T03` Hermes skill `vassago-sc01-design`.
- Add a compile-ready fixture to exercise phase 08 positive path.
- Implement `PT-024.T11` only behind `foundry_allowed=true`.

RESUME FROM HERE:

Start with `PT-026.T03` Hermes skill. Configure it to launch `python -m vassago_contract_runtime.cli mcp --stdio`, call `vassago_design_run`, read `sc01-final-report.json` via `vassago_artifact_read`, and avoid fine-grained phase tools. Current tests are 46 OK and `check` passes before final validation.

## S-20260621-011 - Hermes skill for SC01 design runtime

Goal:

- Implement `PT-026.T03` Hermes skill `vassago-sc01-design` pointing to the local MCP stdio runtime.

What was done:

- Added wrapper `scripts/hermes-vassago-contract-runtime-mcp.cmd`.
- Installed local Hermes skill at `C:\Users\PC\AppData\Local\hermes\skills\domain\vassago-sc01-design\SKILL.md`.
- Added versioned prompt source at `designs/sc01-access/prompts/vassago-sc01-design.md`.
- Registered Hermes MCP server `vassago_contract_runtime` with command `scripts/hermes-vassago-contract-runtime-mcp.cmd`.
- Updated docs/control files.

Decisions:

- The skill starts with `mcp_vassago_contract_runtime_vassago_design_run`.
- It reads `sc01-final-report.json` through `mcp_vassago_contract_runtime_vassago_artifact_read`.
- It escalates to legacy `vassago-sc01-access` only after a final report exists and requests deeper access-control analysis.
- It must not call shell or fine-grained legacy tools while the design-runtime MCP is available.

Validation:

- `hermes mcp test vassago_contract_runtime` connected and discovered 3 tools.
- `hermes skills list` shows `vassago-sc01-design` enabled as a local domain skill.

Blockers:

- Full Hermes LLM smoke has not been run yet in this commit.
- No positive compile-ready fixture exists yet.
- Phase 09 runtime Foundry remains dry-run unless a runtime-ready report and explicit authorization exist.

Next:

- Run an interactive or CLI Hermes smoke with `--skills vassago-sc01-design` against the fixture target.
- Implement `PT-026.T04` A2A card if the skill behavior is acceptable.
- Add a compile-ready fixture to exercise phase 08 positive path.

RESUME FROM HERE:

Start by running a Hermes smoke using `vassago-sc01-design`. Ask it to run the fixture SC01 design through `vassago_contract_runtime`, then verify it used `vassago_design_run` and `vassago_artifact_read` instead of shell. If that passes, implement `PT-026.T04` A2A card.
