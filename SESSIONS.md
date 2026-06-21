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

## S-20260621-012 - Positive SC01 Foundry runtime fixture

Goal:

- Investigate a public SC01 pattern suitable for a safe local positive fixture and prove the design runtime can reach compile-only and local Foundry runtime.

What was done:

- Researched public SC01/proxy access-control patterns and selected the UUPS uninitialized implementation pattern as the safest local fixture basis.
- Added `tests/fixtures/targets_positive.json`.
- Added `tests/fixtures/source_fixture_positive.json` with `FixtureUUPSPositive`.
- Updated `src/vassago_contract_runtime/phases/source_truth.py` with a strictly local-positive source-truth path for `metadata.local_positive_sc01_case=uups_uninitialized_implementation`.
- Updated `src/vassago_contract_runtime/phases/onchain_state.py` to produce fixture state sidecars with no RPC.
- Updated `src/vassago_contract_runtime/phases/proof_pieces.py` so empty `missing_proof_pieces=[]` is treated as complete and can set `foundry_allowed=true`.
- Updated `src/vassago_contract_runtime/phases/compile_only.py` to render a concrete `VassagoSC01Harness.t.sol` for the positive UUPS initializer fixture.
- Added `src/vassago_contract_runtime/phases/runtime_foundry.py` for phase 09 local Foundry runtime.
- Updated `src/vassago_contract_runtime/runtime_api.py`, `src/vassago_contract_runtime/cli.py` and `src/vassago_contract_runtime/tools/runtime_tools.py` to support explicit `runtime_authorized` / `--runtime-authorized`.
- Updated `src/vassago_contract_runtime/phases/final_report.py` so runtime local evidence is reflected as `evidence_status=runtime_local`.
- Added unit coverage in `tests/design_runtime/test_phases.py` for the positive runtime path.

Decisions:

- The positive case is a local regression fixture, not a live-contract claim.
- Runtime remains blocked unless `foundry_allowed=true`, compile-only passed and explicit runtime authorization is present.
- No RPC, private key, fork URL or broadcast is used by this fixture.
- The next production-quality step is replacing the fixture metadata shortcut with source/IR-backed verification.

Validation:

- `$env:PYTHONPATH='src'; python -m unittest tests.design_runtime.test_phases tests.design_runtime.test_provider_adapters tests.design_runtime.test_tool_contracts` passed: 20 tests.
- `$env:PYTHONPATH='src'; python -m unittest discover -s tests` passed: 47 tests.
- `$env:PYTHONPATH='src'; python -m vassago_contract_runtime.cli check` passed.
- `git diff --check` passed, with normal CRLF warnings.
- Real local runtime smoke passed:
  `python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets_positive.json --output runs/sc01-positive-local-runtime --source-fixture tests/fixtures/source_fixture_positive.json --bootstrap-adapters --runtime-authorized`.
- Real Foundry output: `forge test --match-contract VassagoSC01Harness`, 1 test passed, 0 failed, no broadcast.

Blockers:

- Source-truth positive verification is still fixture-scoped and metadata-gated.
- Real contracts need source/IR verification, proxy/state impact and on-chain state readers before runtime.

Next:

- Implement `PT-024.T13`: source/IR-backed verifier for UUPS/uninitialized implementation instead of fixture metadata shortcut.
- Expand SC01 fixture ground truth for tx.origin, missing modifier, weak UUPS, role-admin escalation and public safe lifecycle negatives.
- Run 5 curated real contracts only after the source/IR verifier is available.

RESUME FROM HERE:

Start with `PT-024.T13`. Keep the current positive fixture as regression, but remove reliance on `metadata.local_positive_sc01_case` for anything beyond local tests. Build source/IR checks for `initialize()`, `_disableInitializers()`, owner/admin reader, upgrade sink and authorization path. Do not run real-contract Foundry until source truth, state readers, args, delta and predicate are complete.

## S-20260621-013 - PT-024.T13 source-backed SC01 initializer verifier

Goal:

- Replace the local-positive metadata shortcut with source-backed verification for the UUPS/uninitialized implementation positive path.

What was done:

- Added `src/vassago_contract_runtime/sc01_source.py`.
- Moved UUPS initializer recognition into `evaluate_uninitialized_uups_initializer()`.
- Source-backed checks now require:
  - Solidity compile context marker via `pragma solidity`;
  - external/public `initialize()`;
  - no `_disableInitializers()` marker;
  - initializer write to `owner`, `admin` or `governor`;
  - `owner()`/admin reader via ABI or public source variable;
  - `upgradeTo` or `upgradeToAndCall` sink;
  - `_authorizeUpgrade` source marker;
  - codable initializer args for no-arg or one-address initializer.
- Updated `source_truth.py` to use the verifier instead of `metadata.local_positive_sc01_case`.
- Updated `onchain_state.py` so local fixture state blockers clear only for fixture provider plus source-backed verification. Live providers still require real state/proxy sidecars.
- Updated `compile_only.py` so the initializer harness is rendered from source-backed verification.
- Removed `local_positive_sc01_case` from `tests/fixtures/source_fixture_positive.json`.
- Added `tests/design_runtime/test_sc01_source.py`.

Decisions:

- Source verification is enough to open the local fixture path, but not enough for live-contract runtime. Live targets still need proxy/state impact sidecars.
- The verifier remains deliberately narrow; it is not a general Solidity parser yet.
- Negative lifecycle/accounting policies are a separate next task (`PT-024.T14`).

Validation:

- `$env:PYTHONPATH='src'; python -m unittest tests.design_runtime.test_sc01_source tests.design_runtime.test_phases` passed: 9 tests.
- Old fixture stayed blocked: `foundry_allowed=false`, `runtime_ready_count=0`.
- Positive fixture without metadata shortcut reached `runtime_completed` with local Foundry.

Blockers:

- Need full regression run after this docs update.
- Need source-backed negative policies before running curated real contracts.
- Need Slither/Python IR path for stronger function body/state write extraction.

Next:

- Run full tests, check and diff check.
- Implement `PT-024.T14` source-backed negative verification for public lifecycle/accounting false positives.
- Then expand `PT-027.T01` adversarial fixtures and run `PT-027.T02` on 5 curated real contracts.

RESUME FROM HERE:

Run full validation first: `$env:PYTHONPATH='src'; python -m unittest discover -s tests`, `python -m vassago_contract_runtime.cli check`, and `git diff --check`. Then start `PT-024.T14`: add negative source-truth policies for public deposit/accounting/lifecycle paths so the runtime does not create proof pieces for normal public protocol behavior.

## S-20260621-014 - PT-024.T14 source-backed negative policy

Goal:

- Add source-backed negative verification so normal public protocol/accounting behavior does not reach SC01 proof pieces or Foundry.

What was done:

- Added `evaluate_public_normal_behavior()` in `src/vassago_contract_runtime/sc01_source.py`.
- The negative policy rejects caller-funded accounting/lifecycle-like behavior only when source shows no admin-variable write and no dangerous external sink.
- Integrated negative policy into `src/vassago_contract_runtime/phases/source_truth.py`.
- Source-truth now emits `source_truth_rejected` when all candidates are rejected by negative policy.
- Added anti-hardcode fixture `tests/fixtures/source_fixture_negative.json` and `tests/fixtures/targets_negative.json`.
- Fixture uses `initializeMarket()` so the corpus still produces an initializer-like candidate, but source truth rejects it by effect as `caller_funded_accounting`.
- Added tests in `tests/design_runtime/test_sc01_source.py` and `tests/design_runtime/test_phases.py`.

Decisions:

- Negative policy lives in source truth, not corpus, so future scorers can still queue suspicious items while source truth remains the gate.
- Rejected candidates stay `static_only` and never reach Foundry.
- Admin writes prevent the negative policy from firing, so real initializer/admin cases are not hidden by the public-accounting filter.

Validation:

- `$env:PYTHONPATH='src'; python -m unittest tests.design_runtime.test_sc01_source tests.design_runtime.test_phases` passed: 12 tests.
- CLI smoke on `tests/fixtures/targets_negative.json` produced `source_truth_rejected`, `caller_funded_accounting`, `foundry_allowed=false`.

Blockers:

- Need full regression after docs update.
- Need Slither IR-backed extraction for stronger source truth before curated real contracts.

Next:

- Run full tests, check and diff check.
- Implement `PT-024.T15` Slither IR source extraction.
- Expand `PT-027.T01` fixtures for role escalation, tx.origin, weak UUPS auth, Safe/module and bridge endpoint/source validation.

RESUME FROM HERE:

Run full validation first. Then start `PT-024.T15`: use Slither IR where available to replace regex source body/write/modifier extraction. Keep the positive and negative fixtures as regression gates before any 5-contract real smoke.

## S-20260621-015 - PT-024.T15 normalized Slither IR semantic surface

Goal:

- Prefer Slither IR over heuristic source parsing in phase 02 whenever compile
  context and IR are available.

What was done:

- Updated `src/vassago_contract_runtime/phases/dossier.py` so
  `compile-context.json` becomes `status=available` when source files exist.
- Updated `src/vassago_contract_runtime/phases/semantic_surface.py` so
  `SemanticSurfaceAdapter` accepts an optional `SlitherAdapter`.
- Added normalized IR consumption for `ir.functions[]`, including function
  signatures, modifiers, state writes, calls and source excerpts.
- `access-surface.json` now records:
  - per-function `extraction_source`;
  - `slither.status`;
  - `slither.provider`;
  - Slither function/detector counts.
- If no adapter/IR exists, the phase remains safe and falls back to
  `abi_source_heuristic` or `abi_only`.
- Added regression coverage in `tests/design_runtime/test_phases.py` with a
  fake Slither IR adapter.

Decisions:

- Slither CLI JSON is not treated as full IR because it is detector output.
- The normalized IR contract is now stable; real Python API wiring is a
  separate task (`PT-024.T16`).
- This phase is still `static_only`; no evidence is promoted.

Validation:

- `$env:PYTHONPATH='src'; python -m unittest tests.design_runtime.test_phases tests.design_runtime.test_provider_adapters` passed: 18 tests.
- `$env:PYTHONPATH='src'; python -m unittest tests.design_runtime.test_sc01_source` passed: 5 tests.
- `$env:PYTHONPATH='src'; python -m unittest discover -s tests` passed: 54 tests.
- `$env:PYTHONPATH='src'; python -m vassago_contract_runtime.cli check` passed.
- `git diff --check` passed, with normal CRLF warnings.
- Positive CLI smoke `runs/sc01-positive-t15` completed 11 phases and ran
  local Foundry runtime: `forge test --match-contract VassagoSC01Harness`, 1
  passed, 0 failed, no broadcast.
- Negative CLI smoke `runs/sc01-negative-t15` completed 11 phases and stayed
  `source_truth_rejected`, `foundry_allowed=false`.

Blockers:

- Full Slither Python API extraction is not implemented yet.
- Real curated-contract smoke should wait for `PT-024.T16` or explicit
  degraded-mode approval.

RESUME FROM HERE:

Run full validation: `$env:PYTHONPATH='src'; python -m unittest discover -s tests`,
`python -m vassago_contract_runtime.cli check`, and `git diff --check`. Then
implement `PT-024.T16`: use Slither Python API to populate normalized IR with
modifiers, state reads/writes, calls, inheritance and source refs. Keep CLI JSON
detectors as context, not proof of state writes.

## S-20260621-016 - PT-024.T16 real Slither Python API IR

Goal:

- Use the Slither Python API to populate normalized IR for phase 02 instead of
  relying only on manifest-provided IR or source heuristics.

What was done:

- Added `PythonSlitherAdapter` in
  `src/vassago_contract_runtime/slither/adapter.py`.
- Exported it from `src/vassago_contract_runtime/slither/__init__.py`.
- Wired `SemanticSurfaceAdapter(PythonSlitherAdapter())` in
  `src/vassago_contract_runtime/runtime_api.py` for bootstrap mode.
- Added optional dependency group in `pyproject.toml`: `slither`.
- The adapter now:
  - imports `slither.slither.Slither` optionally;
  - writes source files into an ephemeral workspace;
  - runs from that workspace to avoid Windows absolute-path bugs;
  - returns `unavailable` when Slither is not installed;
  - returns structured `slither_python_analysis_failed` on compiler/source
    failures;
  - normalizes contracts, inheritance, functions, modifiers, state reads,
    state writes, variable reads/writes, internal/external calls, conditions,
    SlithIR operation strings and source mappings.
- Normalized state variable names strip public getter signatures such as
  `owner()` and `balances(address)`.
- Adjusted local positive/negative fixtures to `pragma solidity ^0.8.0` and
  compiler metadata `0.8.20` so the installed Slither/solc path can exercise
  real IR.

Decisions:

- Slither CLI JSON remains detector context only.
- Slither Python output is still `static_only`; it improves source truth inputs
  but does not promote evidence.
- Compiler/version provisioning is separate (`PT-024.T17`) because real
  contracts can require solc versions not installed locally.

Validation:

- `$env:PYTHONPATH='src'; python -m unittest tests.design_runtime.test_provider_adapters tests.design_runtime.test_phases` passed: 19 tests.
- `runs/sc01-positive-t16-real-slither-3` produced:
  `slither.status=completed`, `provider=slither_python`,
  `ir_status=completed`, `initialize().extraction_source=slither_ir`,
  `state_write_signals=["owner"]`, and final `runtime_completed`.
- `runs/sc01-negative-t16-real-slither-2` produced:
  `slither.status=completed`, `initializeMarket().extraction_source=slither_ir`,
  `state_write_signals=["balances", "totalDeposits"]`,
  `source_truth_rejected`, and `foundry_allowed=false`.

Blockers:

- Need full regression after docs update.
- Need `PT-024.T17` for compiler/version selection before broad real-contract
  batches.

RESUME FROM HERE:

Run full validation: `$env:PYTHONPATH='src'; python -m unittest discover -s tests`,
`python -m vassago_contract_runtime.cli check`, and `git diff --check`. Then
implement `PT-024.T17` if real-contract Slither coverage is the priority, or
run `PT-027.T01` fixture expansion if evaluation coverage is the priority.

## S-20260621-017 - PT-024.T17 Slither compiler/version selection

Goal:

- Select the correct installed solc version for Slither Python based on compile
  context, and record the selection in artifacts.

What was done:

- Updated `src/vassago_contract_runtime/phases/dossier.py`:
  - extracts `compiler_version` from source metadata;
  - parses Solidity pragma constraints;
  - writes `solc_version_selection` into `compile-context.json`.
- Updated `src/vassago_contract_runtime/slither/adapter.py`:
  - reads `solc_version_selection`;
  - detects current `solc --version`;
  - sets `SOLC_VERSION` while Slither Python runs;
  - restores cwd and environment after the call;
  - records `compiler_selection` in Slither metadata.
- Updated `src/vassago_contract_runtime/phases/semantic_surface.py` so
  `access-surface.json.slither.compiler_selection` exposes requested/current
  compiler status.
- Added tests for `SOLC_VERSION` scoping/restoration and normalized getter
  names such as `owner()` and `balances(address)`.

Decisions:

- T17 selects installed compiler versions only.
- It does not download missing solc versions or mutate machine-global compiler
  state.
- If Slither cannot compile a real target, the failure remains structured and
  phase 02 falls back to heuristic extraction.
- Compiler cache/provisioning is deferred to `PT-024.T18`, only if curated real
  smoke proves it is necessary.

Validation:

- `$env:PYTHONPATH='src'; python -m unittest tests.design_runtime.test_provider_adapters` passed: 11 tests.
- `$env:PYTHONPATH='src'; python -m unittest tests.design_runtime.test_phases` passed: 8 tests.
- `runs/sc01-positive-t17` completed 11 phases:
  - `compile-context.json` requested `0.8.20`;
  - `slither.compiler_selection.current_solc_version=0.8.20`;
  - `slither.compiler_selection.status=current_matches_requested`;
  - `initialize().extraction_source=slither_ir`;
  - final `runtime_completed`.
- `runs/sc01-negative-t17` completed 11 phases:
  - Slither Python completed;
  - `initializeMarket()` writes `balances` and `totalDeposits` via IR;
  - source truth rejected it as caller-funded accounting;
  - `foundry_allowed=false`.

Blockers:

- Need full regression after docs update.
- Need real-contract smoke to quantify whether missing solc versions are common
  enough to justify `PT-024.T18`.

RESUME FROM HERE:

Run full validation: `$env:PYTHONPATH='src'; python -m unittest discover -s tests`,
`python -m vassago_contract_runtime.cli check`, and `git diff --check`. Then
continue with `PT-027.T01` fixture expansion or `PT-027.T02` 5 curated real
contracts. Only implement `PT-024.T18` if real smoke shows compiler misses.

## S-20260621-018 - PT-024.T18 controlled solc cache/provisioning

Goal:

- Add controlled compiler cache/provisioning for Slither without changing global
  compiler state or downloading compilers by default.

What was done:

- Added `src/vassago_contract_runtime/slither/solc_manager.py`.
- Implemented `SolcSelectManager`:
  - runs `solc-select versions`;
  - reports `compiler_cache_missing` when requested version is absent;
  - runs `solc-select install <version>` only when `allow_install=True`;
  - never calls `solc-select use`;
  - records installed versions and install status.
- Updated `PythonSlitherAdapter`:
  - calls the manager before Slither;
  - records `compiler_selection.provisioning`;
  - skips Slither with structured `solc_version_cache_missing` when a requested
    compiler is unavailable and install is not allowed;
  - still falls back through phase 02 instead of breaking the whole run.
- Added CLI and tool payload field `allow_solc_install`, default `false`.
- Exported `SolcSelectManager`, `SolcVersionManager` and
  `SolcProvisionResult`.
- Added unit tests for cache miss, opt-in install, env restoration and skip
  behavior.

Decisions:

- Default remains deterministic/offline-friendly: no compiler download.
- Explicit `--allow-solc-install` is allowed only as a setup/smoke action.
- The runtime never mutates machine-global solc-select state with
  `solc-select use`; Slither gets version selection through `SOLC_VERSION`.

Validation:

- `$env:PYTHONPATH='src'; python -m unittest tests.design_runtime.test_provider_adapters` passed: 14 tests.
- `$env:PYTHONPATH='src'; python -m unittest tests.design_runtime.test_tool_contracts tests.design_runtime.test_phases` passed: 12 tests.
- `$env:PYTHONPATH='src'; python -m unittest discover -s tests` passed: 58 tests.
- `$env:PYTHONPATH='src'; python -m vassago_contract_runtime.cli check` passed.
- `git diff --check` passed, with normal CRLF warnings.
- `runs/sc01-positive-t18` completed:
  - `provisioning.status=current_matches_requested`;
  - `install_attempted=false`;
  - installed solc-select versions recorded;
  - final `runtime_completed`.
- `runs/sc01-negative-t18` completed:
  - `provisioning.status=current_matches_requested`;
  - `install_attempted=false`;
  - `source_truth_rejected`;
  - `foundry_allowed=false`.

Blockers:

- Need full regression after docs update.
- Need curated real-contract smoke to decide whether a Slither failure summary
  phase/tool is needed.

RESUME FROM HERE:

Run full validation: `$env:PYTHONPATH='src'; python -m unittest discover -s tests`,
`python -m vassago_contract_runtime.cli check`, and `git diff --check`. Then
continue with `PT-027.T01` adversarial fixtures or `PT-027.T02` 5 curated real
contracts. Use `--allow-solc-install` only for explicit setup/smoke, not default
agent runs.

## S-20260621-019 - PT-027.T01 adversarial SC01 fixtures

Goal:

- Add the first local adversarial SC01 fixture slice before running real curated
  contracts, so the design runtime does not promote obvious false positives.

What was done:

- Added corpus records:
  - `designs/sc01-access/corpus/tx-origin-auth.yaml`;
  - `designs/sc01-access/corpus/role-admin-escalation.yaml`;
  - `designs/sc01-access/corpus/public-lifecycle-noise.yaml`.
- Added adversarial fixture targets:
  - `tests/fixtures/targets_adversarial.json`;
  - `tests/fixtures/source_fixture_adversarial.json`.
- Added regression coverage in
  `tests/design_runtime/test_phases.py`:
  `test_adversarial_fixture_suite_routes_without_false_foundry_promotion`.

Fixture behavior:

- `0x4444...4444` has `initialize()` and `upgradeTo(...)`, but constructor
  calls `_disableInitializers()`. It must not become source-truth verified.
- `0x5555...5555` uses `tx.origin == owner`; it routes as
  `tx_origin_authorization` but `foundry_allowed=false`.
- `0x6666...6666` has public `grantOperator(address)`; it routes as
  `role_admin_escalation` but `foundry_allowed=false`.
- `0x7777...7777` has public timestamp-gated `settleRound()`; source truth
  rejects it as `public_lifecycle`.

Decisions:

- This slice is anti-hardcode/false-promotion coverage only.
- It is not live-chain evidence.
- The runtime still requires complete proof pieces before Foundry can run.
- Remaining adversarial cases are split into `PT-027.T01B` instead of claiming
  full SC01 fixture coverage now.

Validation:

- `$env:PYTHONPATH='src'; python -m unittest tests.design_runtime.test_phases -v`
  passed: 9 tests.
- `$env:PYTHONPATH='src'; python -m unittest tests.design_runtime.test_provider_adapters -v`
  passed: 14 tests.
- `$env:PYTHONPATH='src'; python -m unittest discover -s tests` passed:
  59 tests.
- `$env:PYTHONPATH='src'; python -m vassago_contract_runtime.cli check`
  passed: 5/5 checks.
- `git diff --check` passed, with normal CRLF warnings only.
- CLI smoke
  `runs/sc01-adversarial-t27` completed 44 phases, `failed_count=0`,
  `foundry_allowed=false` for all 4 adversarial targets.

Blockers:

- Need `PT-027.T02` smoke on 5 curated real contracts to measure real
  Slither/compiler/import behavior.
- Need `PT-027.T01B` for no-op guard, post-check guard, Safe/module, bridge
  endpoint/source and ERC4337 validator fixtures.

RESUME FROM HERE:

Run full validation: `$env:PYTHONPATH='src'; python -m unittest discover -s tests`,
`python -m vassago_contract_runtime.cli check`, and `git diff --check`. Then run
`PT-027.T02` on 5 curated real contracts. If real targets show repeated
Slither/import/compiler failures, implement `PT-024.T19` summary by target;
otherwise continue with `PT-027.T01B` adversarial fixture expansion.

## S-20260621-020 - PT-025.T01B Explorer-backed SourceResolver

Goal:

- Let `PT-027.T02` run real curated contracts without manually creating source
  fixtures.

What was done:

- Added `ExplorerSourceResolver` in
  `src/vassago_contract_runtime/contracts/source_resolver.py`.
- Exported it from `src/vassago_contract_runtime/contracts/__init__.py`.
- Updated `src/vassago_contract_runtime/runtime_api.py`:
  - use `FixtureSourceResolver` when `source_fixture` exists;
  - otherwise use
    `ExplorerSourceResolver(EtherscanV2ExplorerAdapter(cache_dir=...))`;
  - default cache path is `<output>/_cache/etherscan-v2` for `run-design` and
    `<run>/_cache/etherscan-v2` for `resume`.
- Added CLI option `--source-cache-dir`.
- Added MCP/tool contract input field `source_cache_dir`.
- Added real curated smoke target list:
  `tests/fixtures/targets-curated-real-5.json`.

Decisions:

- Etherscan V2 source resolution is read-only and uses `ETHERSCAN_API_KEY`.
- Cache keys exclude the API key.
- If `ETHERSCAN_API_KEY` is missing, the resolver records structured
  `etherscan_api_key_missing`; it does not create fake source.
- `--source-fixture` remains the deterministic local path for tests.

Validation:

- `$env:PYTHONPATH='src'; python -m unittest tests.design_runtime.test_provider_adapters -v`
  passed: 15 tests.
- `$env:PYTHONPATH='src'; python -m unittest tests.design_runtime.test_phases -v`
  passed: 10 tests.
- No-key smoke
  `runs/sc01-curated-real-5-no-key-smoke` completed 55 phases with
  `failed_count=0`; all 5 `source-manifest.json` files recorded
  `provider=etherscan_v2`, `status=unresolved` and
  `error=etherscan_api_key_missing`.
- `$env:PYTHONPATH='src'; python -m unittest discover -s tests` passed:
  61 tests.
- `$env:PYTHONPATH='src'; python -m vassago_contract_runtime.cli check`
  passed: 5/5 checks.
- `git diff --check` passed, with normal CRLF warnings only.

Blockers:

- Live curated smoke with real source was not run because `ETHERSCAN_API_KEY`
  was not set in the current shell.

RESUME FROM HERE:

Load `ETHERSCAN_API_KEY` in the shell, then run:
`$env:PYTHONPATH='src'; python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets-curated-real-5.json --output runs/sc01-curated-real-5 --bootstrap-adapters`.
After that, inspect `01_dossier/source-manifest.json`,
`02_semantic_surface/access-surface.json` and Slither compiler/provisioning
status for all 5 targets. If failures cluster around compiler/import/source
bundle issues, implement `PT-024.T19` per-target Slither/source summary.

## S-20260621-021 - PT-027.T02 curated 5 real-contract smoke

Goal:

- Run the first 5 real curated contracts through the new contract-first SC01
  runtime using real Etherscan V2 source resolution.

Environment:

- `ETHERSCAN_API_KEY` was present in `C:\Users\PC\Desktop\Vassago\.env`, not in
  the current shell.
- The command loaded `.env` into process environment without printing secrets.

Command:

```powershell
$envFile='C:\Users\PC\Desktop\Vassago\.env'
# load env into process
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets-curated-real-5.json --output runs/sc01-curated-real-5 --bootstrap-adapters
```

What happened:

- First run stopped:
  - `executed_count=45`;
  - `failed_count=2`;
  - both failures were phase `05_source_truth`;
  - error: `missing ), unterminated subpattern at position 8`.
- Root cause was local code:
  `src/vassago_contract_runtime/sc01_source.py`
  `_is_user_funded_accounting()` had malformed regex
  `r"\b\w+\s*(?:\+=|-="`.
- Fixed the regex to include assignment and close the non-capturing group.
- Added regression:
  `SC01SourceVerifierTests.test_public_normal_behavior_handles_plain_assignment_without_regex_error`.
- Resumed the same run:
  - `executed_count=12`;
  - `skipped_count=43`;
  - `failed_count=0`;
  - `status=completed`.

Per-target result:

- ETH EntryPoint v0.6:
  - source resolved via `etherscan_v2`;
  - contract `EntryPoint`;
  - requested solc `0.8.17`;
  - Slither Python completed;
  - 3 thesis candidates;
  - final `blocked_no_runtime_ready`.
- BSC PancakeSwap MasterChefV2:
  - source resolved via `etherscan_v2`;
  - contract `MasterChefV2`;
  - requested solc `0.6.12`;
  - Slither Python completed;
  - 4 thesis candidates;
  - final `blocked_no_runtime_ready`.
- Base Uniswap v4 PoolManager:
  - source resolved via `etherscan_v2`;
  - contract `PoolManager`;
  - requested solc `0.8.26`;
  - Slither Python completed;
  - 4 thesis candidates;
  - final `blocked_no_runtime_ready`.
- ETH Safe Singleton 1.3.0:
  - source resolved via `etherscan_v2`;
  - contract `GnosisSafe`;
  - requested solc `0.7.6`;
  - Slither Python completed;
  - 2 thesis candidates;
  - final `blocked_no_runtime_ready`.
- ETH USDC FiatTokenProxy:
  - source resolved via `etherscan_v2`;
  - contract `FiatTokenProxy`;
  - requested solc `0.4.24`;
  - Slither Python failed with `solc_version_cache_missing`;
  - 2 thesis candidates;
  - final `blocked_no_runtime_ready`.

What worked:

- Real Etherscan V2 source resolution worked for all 5 targets.
- Cache path worked and resume reused prior work.
- Slither Python worked for 4/5 targets.
- No candidate became runtime evidence.
- Runtime/Foundry remained blocked because proof pieces were incomplete.

What failed or is weak:

- USDC needs explicit compiler provisioning for solc `0.4.24`.
- Source-truth is still too narrow and leaves all real candidates as `blocked`;
  this is safe but not yet productive.
- The first real smoke exposed a missing regression around plain assignment
  regex parsing.

Validation:

- `$env:PYTHONPATH='src'; python -m unittest tests.design_runtime.test_sc01_source -v`
  passed: 6 tests.
- `$env:PYTHONPATH='src'; python -m unittest tests.design_runtime.test_phases -v`
  passed: 10 tests.
- `$env:PYTHONPATH='src'; python -m unittest discover -s tests` passed:
  62 tests.
- `$env:PYTHONPATH='src'; python -m vassago_contract_runtime.cli check`
  passed: 5/5 checks.
- `git diff --check` passed, with normal CRLF warnings only.

RESUME FROM HERE:

Decide whether to run `PT-027.T02B` with explicit `--allow-solc-install` so
USDC can install/use solc `0.4.24` for Slither. If not, continue with
`PT-027.T01B` adversarial fixtures or improve source-truth policies for the
real candidate classes observed in `runs/sc01-curated-real-5`. Do not run
Foundry runtime from this smoke; every target ended `foundry_allowed=false`.

## S-20260621-022 - PT-027.T02 real source/Slither smoke closure

Goal:

- Resolve all operational blockers from the 5-contract curated real smoke.
- Keep evidence boundaries strict: no Foundry runtime and no vulnerability
  claim unless `foundry_allowed=true`.

What was done:

- Fixed `src/vassago_contract_runtime/explorer/adapter.py` so flat Etherscan
  source names without suffix become `<ContractName>.sol`; this fixed USDC
  `FiatTokenProxy` Slither input.
- Fixed `src/vassago_contract_runtime/phases/dossier.py` so
  `compile-context.json.selected_source_file` selects the file that declares
  `metadata.contract_name` instead of alphabetic first source.
- Added deterministic remapping inference in
  `compile-context.json.solc_remaps` for source bundles with paths like
  `lib/v4-core/lib/solmate/...`; this fixed Uniswap v4 PoolManager import
  resolution for Slither Python.
- Added/updated regressions in:
  - `tests/design_runtime/test_phases.py`;
  - `tests/design_runtime/test_provider_adapters.py`;
  - `tests/design_runtime/test_sc01_source.py`.

Real command:

```powershell
$envFile='C:\Users\PC\Desktop\Vassago\.env'
# loaded ETHERSCAN_API_KEY into process without printing it
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets-curated-real-5.json --output runs/sc01-curated-real-5-v4 --bootstrap-adapters
```

Result:

- `executed_count=55`;
- `failed_count=0`;
- `status=completed`;
- all 5 sources resolved with `provider=etherscan_v2`;
- all 5 Slither Python runs completed;
- all 5 final reports stayed `blocked_no_runtime_ready`;
- all 5 stayed `foundry_allowed=false`.

Per-target source selection:

- ETH EntryPoint: `contracts/core/EntryPoint.sol`, solc `0.8.17`,
  Slither `completed`.
- BSC MasterChefV2: `contracts/MasterChefV2.sol`, solc `0.6.12`,
  Slither `completed`.
- Base PoolManager: `lib/v4-core/src/PoolManager.sol`, solc `0.8.26`,
  Slither `completed`, remaps include
  `solmate/=lib/v4-core/lib/solmate/`.
- ETH GnosisSafe: `contracts/GnosisSafe.sol`, solc `0.7.6`,
  Slither `completed`.
- ETH FiatTokenProxy: `FiatTokenProxy.sol`, solc `0.4.24`,
  Slither `completed`.

Validation:

- `$env:PYTHONPATH='src'; python -m unittest discover -s tests` passed:
  63 tests.
- `$env:PYTHONPATH='src'; python -m vassago_contract_runtime.cli check`
  passed: 5/5 checks.
- `git diff --check` passed, with CRLF warnings only.

Decisions:

- Treat `runs/sc01-curated-real-5-v4` as the current real smoke baseline.
- Do not run Foundry from this sample; every target lacks complete proof
  pieces.
- Next implementation work should improve source-truth/proof-piece productivity
  or expand adversarial/metamorphic fixtures, not bypass the runtime gate.

RESUME FROM HERE:

Use `runs/sc01-curated-real-5-v4` as the current real baseline. If continuing
SC01 quality, inspect why source truth produced zero verified hypotheses for
these 5 real targets and add targeted source-truth policies or stronger corpus
records. If continuing validation, expand `PT-027.T01B` adversarial/metamorphic
fixtures. Do not run Foundry runtime unless a fresh report has
`foundry_allowed=true`.
