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

## S-20260621-023 - PT-027.T03 20-contract curated SC01 smoke

Goal:

- Commit the first validated runtime/source/Slither slice.
- Analyze blockers from the 5 real curated contracts.
- Harden the correct mappers/source-truth policies.
- Run 20 curated real contracts across ETH/BSC/Base and record real results.

What was committed first:

- Commit `e30a5af` with message
  `feat(runtime): validate real explorer source and slither smoke`.
- Pre-commit validation:
  - `$env:PYTHONPATH='src'; python -m unittest discover -s tests`:
    63 passed;
  - `$env:PYTHONPATH='src'; python -m vassago_contract_runtime.cli check`:
    passed 5/5;
  - `git diff --check`: passed with CRLF warnings only;
  - staged added-line secret scan: no added secret-like lines.

Blocker analysis from 5 real targets:

- Broad corpus matches were too noisy because phase 03 matched global source
  text. EntryPoint, GnosisSafe and other targets could emit candidates without
  function-level evidence.
- Uniswap v4 PoolManager `initialize(tuple,uint160)` is a protocol pool
  initializer, not proxy/admin initialization.
- PoolManager `settle/settleFor` and MasterChef-like flows are public
  accounting/lifecycle behavior, not authorization gaps.
- `setOperator`/approval APIs are caller-scoped token/operator behavior, not
  role-admin escalation.
- USDC/Aave-style transparent proxy upgrade functions are admin-gated proxy
  paths, not weak UUPS authorization.

Code changes in the second slice:

- `src/vassago_contract_runtime/phases/corpus_motifs.py` now builds thesis
  candidates from function-level evidence in `access-surface.json`.
- `src/vassago_contract_runtime/sc01_source.py` now rejects:
  - no function-level evidence;
  - transparent proxy admin path;
  - initialized EIP-1967 proxy with explorer implementation context;
  - protocol pool initializer;
  - public factory/pool creation;
  - token approval/operator APIs;
  - caller-funded accounting, protocol lock accounting and caller-scoped
    operator behavior.
- `src/vassago_contract_runtime/phases/source_truth.py` consumes those
  negative policies and emits terminal `source_truth_rejected` records.
- `src/vassago_contract_runtime/explorer/adapter.py` normalizes Etherscan
  standard JSON absolute source-unit names.
- `src/vassago_contract_runtime/phases/dossier.py` improves remapping inference
  for Uniswap/OpenZeppelin nested package layouts.
- `tests/fixtures/targets-curated-real-20.json` adds 20 curated ETH/BSC/Base
  targets.

Real command:

```powershell
$envFile='C:\Users\PC\Desktop\Vassago\.env'
# loaded ETHERSCAN_API_KEY into process without printing it
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets-curated-real-20.json --output runs/sc01-curated-real-20-v8 --bootstrap-adapters --allow-solc-install
```

Result:

- `executed_count=220`;
- `failed_count=0`;
- `status=completed`;
- all 20 source bundles resolved through `etherscan_v2`;
- all 20 Slither Python runs completed;
- 13 SC01 thesis candidates reached source-truth review;
- all 13 were `source_truth_rejected`;
- all 20 final reports are `blocked_no_runtime_ready`;
- all 20 have `foundry_allowed=false`;
- `runtime_ready_total=0`.

Source-truth rejection classes in v8:

- `transparent_proxy_admin_path`: 3;
- `public_lifecycle`: 2;
- `caller_funded_accounting`: 2;
- `public_factory_or_pool_creation`: 2;
- `caller_scoped_operator`: 1;
- `token_approval_operator`: 1;
- `protocol_pool_initializer`: 1;
- `initialized_eip1967_proxy`: 1.

Decisions:

- Treat `runs/sc01-curated-real-20-v8` as the current curated real baseline.
- Do not run Foundry from this baseline. The correct result is terminal
  rejection of broad false candidates.
- Next productive work is high-signal acquisition, not larger random batches:
  weak/ambiguous `_authorizeUpgrade`, initialized proxy state impact, concrete
  role-admin graph, Safe/AA/module sidecars with measurable deltas.

RESUME FROM HERE:

Run the final validation and commit the second slice if not already committed:
`python -m unittest discover -s tests`, `python -m vassago_contract_runtime.cli check`,
and `git diff --check`. Use `runs/sc01-curated-real-20-v8` as the current
20-target baseline. Do not run Foundry unless a fresh final report has
`foundry_allowed=true`. Next feature work should implement high-signal target
acquisition, not another random contract batch.

## S-20260621-024 - PT-027.T05 historical SC01 runtime suite

Goal:

- Add a small curated historical SC01 suite and verify whether the new design
  runtime can reach local Foundry evidence on a known access-control class.

What was added:

- `tests/fixtures/targets-sc01-historical-6.json` with:
  - BadgerDAO `WarRoomGatedProxy`;
  - Audius `AudiusAdminUpgradeabilityProxy`;
  - Nomad `UpgradeBeaconProxy` / Replica context;
  - Furucombo `Proxy`;
  - Alchemix `AlchemixHarvester`;
  - Wormhole `Wormhole`.

Code changes:

- `src/vassago_contract_runtime/sc01_source.py`:
  - added `evaluate_access_control_initializer()`;
  - recognizes external/public `initialize` with `initializer` modifier and
    `_setupRole(DEFAULT_ADMIN_ROLE, ...)`;
  - supports codable `address` and `address[]` initializer args.
- `src/vassago_contract_runtime/phases/source_truth.py`:
  - verifies `access_control_uninitialized_initializer` for the
    `uninitialized_implementation_proxy` thesis.
- `src/vassago_contract_runtime/phases/onchain_state.py`:
  - emits local initializer state sidecars without provider blockers when
    source truth is verified;
  - explicitly marks this as local reproduction state, not live impact.
- `src/vassago_contract_runtime/phases/compile_only.py`:
  - renders an AccessControl initializer harness that asserts
    `hasRole(DEFAULT_ADMIN_ROLE, address(this))`.
- `src/vassago_contract_runtime/phases/runtime_foundry.py`:
  - reads predicate and measured delta from the verified source-truth review
    instead of hardcoded `owner()` wording.

Focused tests:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.design_runtime.test_sc01_source tests.design_runtime.test_phases
python -m unittest tests.design_runtime.test_provider_adapters
```

Observed:

- 25 tests passed in source/phases.
- 16 tests passed in provider adapters.

Historical run:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets-sc01-historical-6.json --output runs/sc01-historical-6-v4-runtime --bootstrap-adapters --allow-solc-install --runtime-authorized
```

Observed:

- `executed_count=66`;
- `failed_count=0`;
- `source_resolved=6/6`;
- `slither_completed=5/6`;
- `source_truth_verified_total=1`;
- `runtime_ready_total=1`;
- `foundry_allowed=1`;
- `compile_passed=1`;
- `runtime_completed=1`.

Concrete local runtime evidence:

- Target: BadgerDAO `WarRoomGatedProxy`.
- Predicate:
  `After an unauthorized caller invokes initialize(), hasRole(DEFAULT_ADMIN_ROLE, caller) is true.`
- Delta:
  `hasRole(DEFAULT_ADMIN_ROLE, unauthorized caller) changes false to true`.
- Evidence status: `runtime_local`.
- Broadcast: no.

Decisions:

- This is the first real historical SC01 target in the new design runtime that
  reaches local Foundry execution.
- It is not a live impact claim. Live funds-at-risk needs separate chain state,
  proxy/state and asset analysis.
- Do not broaden this into generic initializer promotion. The verifier requires
  role setup, role reader, codable args and a concrete predicate.

Blockers left:

- Audius needs a proxy/governance implementation-state mapper.
- Nomad needs bridge root/proof mapper and Slither failure triage.
- Furucombo needs delegatecall/proxy-storage mapper.
- Alchemix needs keeper actor/delta mapper.
- Wormhole needs implementation initializer/UUPS context mapper.

RESUME FROM HERE:

Commit PT-027.T05 after running the full gate:
`python -m unittest discover -s tests`,
`python -m vassago_contract_runtime.cli check`, and `git diff --check`.
Use `runs/sc01-historical-6-v4-runtime` as the current historical runtime
baseline. Next implementation work should target one blocker mapper at a time:
Audius governance/proxy, Nomad bridge root/proof, Furucombo delegatecall,
Alchemix keeper, or Wormhole implementation/UUPS context.

## S-20260621-025 - PT-027.T06 Audius proxy collision base

Goal:

- Investigate and prepare the Audius historical SC01 blocker without claiming
  reproduction.

Research summary:

- Audius is not a weak UUPS `_authorizeUpgrade` case. The relevant class is
  proxy storage collision plus delegatecall initializer replay: proxy-side
  `proxyAdmin` storage collides with implementation-side `Initializable` flags,
  allowing a delegated initializer path to mutate privileged governance state.
- Wormhole remains a separate uninitialized implementation / UUPS-like context.

Code changes:

- Added
  `designs/sc01-access/corpus/proxy-storage-collision-reinitializer.yaml`.
- Updated `designs/sc01-access/corpus/uups-weak-auth.yaml` with a negative
  signal for custom proxy-admin upgrade paths.
- Updated `src/vassago_contract_runtime/phases/dossier.py`:
  `DossierAdapter` now enriches `source-manifest.json` with
  `related_sources.implementation` when Explorer reports
  `proxy_context.implementation`.
- Updated `src/vassago_contract_runtime/phases/corpus_motifs.py`:
  the new proxy collision thesis requires function-level `proxyAdmin`
  evidence, avoiding broad delegatecall matches.
- Updated `src/vassago_contract_runtime/sc01_source.py`:
  - `evaluate_known_non_sc01_pattern()` rejects Audius `upgradeTo(address)`
    as `custom_proxy_admin_path`;
  - `evaluate_proxy_storage_collision_reinitializer()` detects proxy-side
    storage/delegatecall evidence, related implementation source,
    Initializable slot-zero flags, `Governance.initialize(...)`, and
    privileged initializer writes with readers.
- Updated `src/vassago_contract_runtime/phases/source_truth.py`:
  Audius emits `source_truth_blocked_proxy_side_verified` with implementation
  fields and remaining blockers.
- Updated `tests/design_runtime/test_sc01_source.py` with regression coverage
  for custom proxy-admin paths and Audius-style privileged initializer writes.

Focused tests:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.design_runtime.test_sc01_source
python -m unittest tests.design_runtime.test_phases
```

Observed:

- `test_sc01_source`: 17 passed.
- `test_phases`: 11 passed.

Live historical run:

```powershell
# loaded ETHERSCAN_API_KEY from C:\Users\PC\Desktop\Vassago\.env without printing it
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets-sc01-historical-6.json --output runs/sc01-historical-6-v9-audius-privileged-writes-live --bootstrap-adapters --allow-solc-install --runtime-authorized
```

Observed:

- `executed_count=66`;
- `failed_count=0`;
- Audius proxy source resolved through Etherscan V2;
- Audius implementation source resolved as `Governance` at
  `0x1c91af03a390b4c619b444425b3119e553b5b44b`;
- UUPS review rejected as `custom_proxy_admin_path`;
- proxy collision review status:
  `source_truth_blocked_proxy_side_verified`;
- `initializer_privileged_writes` include:
  `registry`, `votingPeriod`, `executionDelay`,
  `maxInProgressProposals`, `votingQuorumPercent`, `guardianAddress`;
- remaining blockers:
  `proxy_delegatecall_initializer_calldata_required` and
  `measurable_proxy_state_delta_required`;
- Audius `foundry_allowed=false`;
- Badger remains the only runtime-local reproduced case.

Decision:

- Do not run Audius Foundry yet. The base is ready only up to
  source/implementation/write readiness. Runtime needs a dedicated mapper for
  delegatecall initializer calldata and measurable proxy-state delta.

Blockers:

- `ETHERSCAN_API_KEY` is not present in the repo-new shell by default. For live
  runs, load it from `C:\Users\PC\Desktop\Vassago\.env` without printing it.
- Audius needs `PT-027.T07` before compile/runtime.

RESUME FROM HERE:

Run full validation and commit this slice if not already committed:
`python -m unittest discover -s tests`,
`python -m vassago_contract_runtime.cli check`, and `git diff --check`.
Use `runs/sc01-historical-6-v9-audius-privileged-writes-live` as the Audius
readiness baseline. Next implementation: `PT-027.T07`, deriving proxy fallback
initializer calldata and measurable reader deltas for Audius-style storage
collision. Do not claim Audius reproduction until runtime-local evidence exists.

## S-20260621-026 - PT-027.T07 Audius proxy collision runtime mapper

Goal:

- Convert Audius proxy-storage-collision readiness into a gated local/fork
  runtime reproduction without broadcast and without leaking RPC secrets.

What changed:

- Added `src/vassago_contract_runtime/sc01_proxy_collision.py`.
- Moved Audius proxy-collision logic out of `sc01_source.py`.
- `source_truth.py` now marks the Audius proxy-collision thesis as
  `source_truth_verified` only when the proxy side, related implementation
  source, initializer call plan and measurable reader delta are complete.
- `compile_only.py` renders an interface-only
  `VassagoSC01Harness.t.sol` for Audius instead of compiling the whole
  implementation as the test target.
- `runtime_foundry.py` passes fork config only after `foundry_allowed=true`,
  compile pass and explicit `--runtime-authorized`.
- `foundry/adapter.py` redacts the `--fork-url` argument in
  `FoundryRunResult.to_json()`.

Runtime mapper details:

- Historical proxy: `0x4DEcA517D6817B6510798b7328F2314d3003AbAC`.
- Implementation: `0x1c91af03a390b4c619b444425b3119e553b5b44b`.
- Fork block: `15201793`.
- Harness call:
  `initialize(address(this), 3, 0, 1, 4, address(this))`.
- Assertions:
  `getGuardianAddress()==address(this)`,
  `getVotingPeriod()==3`,
  `getExecutionDelay()==0`,
  `getVotingQuorumPercent()==1`,
  `getMaxInProgressProposals()==4`,
  `getRegistryAddress()==address(this)`.

Validation:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.design_runtime.test_sc01_source tests.design_runtime.test_phases tests.design_runtime.test_provider_adapters
python -m vassago_contract_runtime.cli check
```

Observed:

- focused tests: `45 passed`;
- runtime check: `status=passed`, `failed_count=0`;
- `sc01_source.py` is 477 lines;
- `sc01_proxy_collision.py` is 252 lines.

Historical runtime run:

```powershell
# loaded ETHERSCAN_API_KEY and VASSAGO_FORK_RPC_* from C:\Users\PC\Desktop\Vassago\.env without printing values
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets-sc01-historical-6.json --output runs/sc01-historical-6-v11-audius-runtime --bootstrap-adapters --allow-solc-install --runtime-authorized
```

Observed:

- run id: `RUN-c3c0ace00102`;
- `executed_count=66`;
- `failed_count=0`;
- Audius target id: `CT-3f08e02c1bef`;
- final report:
  `runs/sc01-historical-6-v11-audius-runtime/targets/CT-3f08e02c1bef/phases/10_final_report/sc01-final-report.json`;
- `compile_status=compile_only_passed`;
- `runtime_status=runtime_completed`;
- `assertion-result.status=passed`;
- `evidence_status=runtime_local`;
- `no_broadcast=true`;
- Foundry output: 1 test passed, 0 failed.

Security checks:

- Foundry command in artifact stores `--fork-url <redacted-rpc-url>`.
- Scan against loaded `.env` values found no `ETHERSCAN_API_KEY` or
  `VASSAGO_FORK_RPC_FALLBACK_ETH_URL` in the Audius target artifacts.

Decision:

- Audius is now reproduced locally on a historical fork for the initializer
  replay proxy-collision thesis.
- Do not present this as current live funds-at-risk. It is historical/fork
  evidence only.

Blockers:

- Remaining historical blockers are still protocol-specific:
  Nomad bridge root/proof, Furucombo delegatecall/proxy-storage,
  Alchemix keeper actor/state delta and Wormhole implementation/UUPS context.

RESUME FROM HERE:

Run the full suite before committing if not already done:
`python -m unittest discover -s tests`,
`python -m vassago_contract_runtime.cli check`, and `git diff --check`.
Use `runs/sc01-historical-6-v11-audius-runtime` as the current Audius runtime
baseline. Next productive blocker is either Wormhole implementation/UUPS
context or Nomad bridge root/proof mapper. Keep runtime local/fork only, with
no broadcast and no severity claim without explicit impact review.

## S-20260621-027 - Audius impact review + Wormhole implementation context

Goal:

- Add a conservative impact review for the reproduced Audius historical case.
- Move the next historical blocker, Wormhole, past the empty-queue state by
  indexing proxy implementation context.

What changed:

- Added `src/vassago_contract_runtime/sc01_impact.py`.
- Added CLI command `impact-review`.
- Added `tests/design_runtime/test_sc01_impact.py`.
- `DossierAdapter` now includes implementation ABI functions/events when
  Explorer reports `proxy_context.implementation`.
- `SemanticSurfaceAdapter` searches `related_sources.*.source_files`.
- `sc01_source.py` now evaluates effective proxy + implementation ABI/source.
- Added `evaluate_wormhole_uninitialized_implementation()`.
- `SourceTruthAdapter` can emit
  `source_truth_verified_runtime_blocked` for Wormhole.

Audius impact review command:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli impact-review --run runs/sc01-historical-6-v11-audius-runtime --target-id CT-3f08e02c1bef
```

Audius impact artifact:

```text
runs/sc01-historical-6-v11-audius-runtime/targets/CT-3f08e02c1bef/phases/11_impact_review/sc01-impact-review.json
```

Observed Audius result:

- `verdict=historical_reproduced_critical`;
- `historical_impact.severity=critical_historical`;
- `current_live_risk.status=not_claimed`;
- `local_reproduction.status=runtime_completed`;
- `local_reproduction.assertion_status=passed`;
- `no_broadcast=true`.

Wormhole rerun command:

```powershell
$env:PYTHONPATH='src'
$env:ETHERSCAN_API_KEY = 'cache-only-placeholder'
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets-sc01-historical-6.json --output runs/sc01-historical-6-v14-wormhole-source-truth --bootstrap-adapters --source-cache-dir runs/sc01-historical-6-v11-audius-runtime/_cache/etherscan-v2
```

Observed Wormhole result:

- `queue_count=3`;
- `source_truth_verified_count=1`;
- evidence kind: `wormhole_uninitialized_implementation`;
- `foundry_allowed=false`;
- blockers are now specific:
  `wormhole_governance_vm_payload_builder`,
  `malicious_initializer_implementation_contract`,
  `runtime_runner_wormhole_uninitialized_implementation`.

Validation:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.design_runtime.test_sc01_source tests.design_runtime.test_phases tests.design_runtime.test_sc01_impact
python -m vassago_contract_runtime.cli check
```

Observed:

- focused tests: `32 passed`;
- check: `status=passed`, `failed_count=0`.

Decisions:

- Audius is historical reproduced critical, not current live severity.
- Wormhole should not run Foundry yet. It needs a dedicated VM/payload builder
  and malicious implementation harness before runtime.
- Use implementation-aware indexing for all proxy targets going forward.

Blockers:

- `ETHERSCAN_API_KEY` is not loaded by default in a fresh shell. Existing cache
  can be reused with a non-secret cache-only placeholder, but fresh Explorer calls
  need the real key loaded securely.

RESUME FROM HERE:

Run full regression before commit:
`$env:PYTHONPATH='src'; python -m unittest discover -s tests`,
`$env:PYTHONPATH='src'; python -m vassago_contract_runtime.cli check`, and
`git diff --check`. Then commit this slice. Next implementation is the
Wormhole runtime builder: generate governance VM payload scaffolding,
malicious initializer implementation contract and a local-only Foundry runner.

## 2026-06-21 - PT-027.T10 Wormhole Runtime Runner

Goal:

- Implement the Wormhole-specific local/fork Foundry runner requested after
  `PT-027.T09`.

What was done:

- Added `src/vassago_contract_runtime/sc01_wormhole.py`.
- Added a self-contained Solidity harness that:
  - uses `vm.load(proxy, EIP1967_IMPLEMENTATION_SLOT)` to resolve the
    historical implementation at fork time;
  - calls implementation `initialize(address[],uint16,uint16,bytes32)`;
  - creates a local attacker guardian with `vm.addr`/`vm.sign`;
  - builds a governance VM payload for `submitContractUpgrade(bytes)`;
  - deploys a `MaliciousImplementation` whose initializer delegatecalls a
    `Destructor.selfdestruct`;
  - asserts implementation code is destroyed on the fork.
- Wired Wormhole harness selection into:
  - `src/vassago_contract_runtime/phases/compile_only.py`;
  - `src/vassago_contract_runtime/phases/runtime_foundry.py`.
- Changed Wormhole source truth from blocked runtime pieces to:
  - `runtime_runner=wormhole_implementation_runtime`;
  - `fork_block_number=13818843`;
  - `runtime_strategy=historical_fork_interface_only`.
- Added Wormhole runner support in
  `src/vassago_contract_runtime/phases/onchain_state.py`.
- Added tests in:
  - `tests/design_runtime/test_sc01_source.py`;
  - `tests/design_runtime/test_phases.py`.

Validation so far:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.design_runtime.test_sc01_source tests.design_runtime.test_phases
```

Observed:

```text
32 tests passed
```

Decisions and reasoning:

- The harness is interface-only. Current Etherscan source is the patched
  implementation and must not be compiled as if it were the historical target.
- The fork block is fixed at `13_818_843`, matching the historical PoC window
  before Wormhole initialized the implementation.
- No broadcast, no private key, no raw transaction and no live chain write are
  used. The guardian key is a local Foundry test key only.

Blockers / in progress:

- Real fork smoke has not yet been run in this slice.
- It requires an archive-capable Ethereum RPC in
  `VASSAGO_FORK_RPC_URL` or `VASSAGO_FORK_RPC_FALLBACK_ETH_URL`.
- If the provider cannot serve block `13_818_843`, the runtime result must be
  `blocked` or `inconclusive`, not reproduced.

RESUME FROM HERE:

Run full regression:
`$env:PYTHONPATH='src'; python -m unittest discover -s tests`;
`$env:PYTHONPATH='src'; python -m vassago_contract_runtime.cli check`;
`git diff --check`.
If the env has an archive Ethereum fork URL, run historical-6 with
`--runtime-authorized` into a new `runs/sc01-historical-6-v15-wormhole-runtime`
artifact and inspect target `CT-24700f446e33`.

## 2026-06-21 - PT-027.T10 Wormhole Runtime Smoke + Impact

Goal:

- Run the Wormhole-specific harness on a real historical fork and separate
  runtime evidence from impact/severity wording.

What was done:

- Loaded fork RPCs from the old Vassago `.env` into the process without printing
  values.
- Ran:
  `python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets-sc01-historical-6.json --output runs/sc01-historical-6-v16-wormhole-runtime --bootstrap-adapters --source-cache-dir runs/sc01-historical-6-v11-audius-runtime/_cache/etherscan-v2 --runtime-authorized`.
- Initial v15 runtime failed because the test asserted `implementation.code.length == 0`
  inside the same transaction. That was the wrong measurable predicate for the
  Foundry test boundary.
- Adjusted the Wormhole harness to write and assert a deterministic marker in
  implementation storage during malicious delegatecall.
- Kept the selfdestruct path in the malicious initializer, but no longer uses
  same-transaction code deletion as the assertion.
- Added Wormhole-specific impact review in
  `src/vassago_contract_runtime/sc01_impact.py`.
- Generated impact artifacts under
  `runs/sc01-historical-6-v16-wormhole-runtime/targets/CT-24700f446e33/phases/11_impact_review/`.

Observed:

- run id: `RUN-07be0359b9b4`;
- executed phases: `66`;
- failed phases: `0`;
- Wormhole compile: `compile_only_passed`;
- Wormhole runtime: `runtime_completed`;
- assertion: `passed`;
- Foundry test:
  `[PASS] testWormholeImplementationInitializerReplayExecutesMaliciousDelegatecall()`;
- impact review verdict: `historical_reproduced_critical`;
- current live risk: `not_claimed`;
- broadcast: no.

Decision:

- Wormhole is now historically reproduced in local fork as SC01 runtime
  evidence.
- Severity wording must remain historical unless current live state is
  independently revalidated.
- Nomad remains a separate bridge root/proof mapper; do not generalize the
  Wormhole VM runner.

RESUME FROM HERE:

Run final regression after this slice:
`$env:PYTHONPATH='src'; python -m unittest discover -s tests`;
`$env:PYTHONPATH='src'; python -m vassago_contract_runtime.cli check`;
`git diff --check`.
If clean, commit with a message like
`feat(sc01): add wormhole historical runtime runner`.
Next technical task: Nomad bridge root/proof mapper, not another Wormhole
iteration.

## 2026-06-21 - PT-027.T11 Nomad Bridge Root/Proof Runtime Mapper

Goal:

- Implement Nomad as a separate bridge root/proof mapper, not as a Wormhole
  initializer/VM variant.

What was done:

- Added `src/vassago_contract_runtime/sc01_nomad.py`.
- Added `designs/sc01-access/corpus/bridge-root-proof-validation.yaml`.
- Integrated Nomad into:
  - `src/vassago_contract_runtime/phases/source_truth.py`;
  - `src/vassago_contract_runtime/phases/compile_only.py`;
  - `src/vassago_contract_runtime/phases/runtime_foundry.py`;
  - `src/vassago_contract_runtime/phases/onchain_state.py`;
  - `src/vassago_contract_runtime/sc01_impact.py`.
- Added tests in:
  - `tests/design_runtime/test_sc01_source.py`;
  - `tests/design_runtime/test_phases.py`;
  - `tests/design_runtime/test_sc01_impact.py`.
- Ran a real local/fork runtime smoke:
  `runs/sc01-historical-6-v18-nomad-runtime`.
- Generated Nomad impact review:
  `runs/sc01-historical-6-v18-nomad-runtime/targets/CT-05f41610b129/phases/11_impact_review/sc01-impact-review.json`.

Observed:

- run id: `RUN-881c3ae4d0ba`;
- target id: `CT-05f41610b129`;
- source truth:
  - `uninitialized_implementation_proxy` rejected;
  - `bridge_root_proof_validation` verified;
- compile: `compile_only_passed`;
- runtime: `runtime_completed`;
- assertion: `passed`;
- Foundry:
  `[PASS] testNomadProcessesUnprovenForgedMessageOnHistoricalFork()`;
- evidence status: `runtime_local`;
- impact verdict: `historical_reproduced_critical`;
- current live risk: `not_claimed`;
- broadcast: no.

Decisions and reasoning:

- Nomad is not an initializer bug. The runtime checks a bridge
  message-authentication predicate: an unproven forged message is accepted by
  historical root/status handling.
- Current source resolves to a fixed Replica implementation. Therefore source
  truth is scoped to the known historical target and runtime proof on a pinned
  fork block `15_259_100`.
- No current live exploitability is claimed.

Blockers / next:

- Remaining historical blockers are Furucombo delegatecall/proxy-storage and
  Alchemix keeper-state.
- For future bridge work, build proof/root/processed-message mappers rather
  than initializer heuristics.

RESUME FROM HERE:

Run final regression:
`$env:PYTHONPATH='src'; python -m unittest discover -s tests`;
`$env:PYTHONPATH='src'; python -m vassago_contract_runtime.cli check`;
`git diff --check`.
If clean, commit with
`feat(sc01): add nomad bridge root proof runtime`.

## 2026-06-22 - PT-027.T12/T13 Furucombo + Alchemix Runtime Mappers

Goal:

- Implement the next two historical SC01 mappers:
  Furucombo delegatecall/proxy-storage and Alchemix keeper-state.

What was done:

- Added:
  - `src/vassago_contract_runtime/sc01_furucombo.py`;
  - `src/vassago_contract_runtime/sc01_alchemix.py`;
  - `designs/sc01-access/corpus/furucombo-delegatecall-proxy-storage.yaml`;
  - `designs/sc01-access/corpus/alchemix-keeper-state.yaml`;
  - `SC01_HISTORICAL_REPRODUCTION_REPORT.md`.
- Integrated both mappers into source truth, compile-only, runtime Foundry,
  on-chain state and impact review.
- Corrected `tests/fixtures/targets-sc01-historical-6.json`:
  - vulnerable historical Furucombo proxy:
    `0x17e8Ca1b4798B97602895f63206afCd1Fc90Ca5f`;
  - post-mortem redeployed proxy:
    `0xA013AfbB9A92cEF49e898C87C060e6660E050569`.

Observed:

- unit: `python -m unittest tests.design_runtime.test_sc01_source` -> `23 OK`;
- real run: `runs/sc01-historical-6-v22-furucombo-alchemix-runtime`;
- Furucombo: `compile_only_passed`, `runtime_completed`, assertion `passed`,
  `[PASS] testFurucomboWhitelistedProxyDelegatecallDrainsVictimAllowance()`;
- Alchemix: `compile_only_passed`, `runtime_completed`, assertion `passed`,
  `[PASS] testAlchemixGenericKeeperCanTriggerLowMinHarvest()`;
- broadcast: no;
- current live risk: `not_claimed`.

RESUME FROM HERE:

Run final regression:
`$env:PYTHONPATH='src'; python -m unittest discover -s tests`;
`$env:PYTHONPATH='src'; python -m vassago_contract_runtime.cli check`;
`git diff --check`.
If clean, commit with
`feat(sc01): add furucombo and alchemix historical runtimes`.

## 2026-06-22 - PT-027.T15 Nomad Root/Proof Analysis Sidecars

Goal:

- Strengthen the Nomad bridge root/proof mapper and make current-state review
  explicit without changing the historical evidence gate.

What was done:

- Added `build_nomad_root_proof_analysis()` in
  `src/vassago_contract_runtime/sc01_nomad.py`.
- `SourceTruthAdapter` now writes
  `nomad-root-proof-analysis.json` for `bridge_root_proof_validation`.
- `OnChainStateAdapter` now writes `bridge-state-review.json` for Nomad.
- Corrected misleading Nomad state labels from `local_initializer_*` to
  protocol-specific bridge/message-authentication statuses.
- Updated `designs/sc01-access/design.yaml` so phase 06 declares
  `bridge-state-review.json`.

Decisions and reasoning:

- The best next step was not another runtime replay. Nomad already reproduced
  historically. The missing piece was a stable, auditable root/proof sidecar
  and a clear list of current-state checks required before any live-risk claim.
- The current-state review remains `not_performed`; this is intentional and
  prevents historical proof from becoming a live exploitability claim.

Validation:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.design_runtime.test_sc01_source tests.design_runtime.test_phases
```

Observed:

```text
38 tests passed
```

Real sidecar smoke:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets-sc01-historical-6.json --output runs/sc01-historical-6-v23-nomad-sidecars --source-cache-dir runs/source-cache-v20 --bootstrap-adapters
```

Observed:

```text
status=completed
failed_count=0
Nomad nomad-root-proof-analysis.status=historical_runtime_ready
Nomad bridge-state-review.status=historical_fork_state_ready_current_live_not_claimed
Nomad admin-state.status=protocol_specific_admin_state_not_required
Nomad final_status=runtime_ready_pending_local_execution
Nomad runtime_status=blocked_runtime_authorization_required
```

RESUME FROM HERE:

Run full regression:
`$env:PYTHONPATH='src'; python -m unittest discover -s tests`;
`$env:PYTHONPATH='src'; python -m vassago_contract_runtime.cli check`;
`git diff --check`.
If clean, commit with
`feat(sc01): add nomad root proof sidecars`.

## 2026-06-22 - PT-027.T16 Nomad Current-State Read-Only Review

Goal:

- Test whether Nomad's historical default-root path still indicates current
  live risk, using read-only calls only.

What was done:

- Added `src/vassago_contract_runtime/sc01_current_state.py`.
- Added CLI command `current-state-review`.
- Added a unit test using fake RPC for the Nomad current-state gate.
- Ran real read-only current-state review against
  `runs/sc01-historical-6-v23-nomad-sidecars`, target
  `CT-05f41610b129`.

Command:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli current-state-review --run runs/sc01-historical-6-v23-nomad-sidecars --target-id CT-05f41610b129
```

Observed:

```text
review_id=CSR-f8f008ef218c
current_block_number=25372508
implementation=0x7f221a1850c12b57fed1f0831dd25399a13b68c2
acceptableRoot(bytes32(0))=false
confirmAt(bytes32(0))=1
messages(forged_message_hash)=0x0000000000000000000000000000000000000000000000000000000000000000
verdict=current_default_root_path_rejected
current_live_risk=not_indicated_by_current_default_root_probe
```

Decision:

- The current source still uses `acceptableRoot(messages[messageHash])`, but
  the current implementation rejects `LEGACY_STATUS_NONE/default root`.
- Because the forged unproven message cannot pass the root gate, no
  asset-moving recipient proof is required for this path.
- Nomad remains `historical_reproduced_critical` with current live risk
  rejected for the default-root path tested here.

RESUME FROM HERE:

Run full regression:
`$env:PYTHONPATH='src'; python -m unittest discover -s tests`;
`$env:PYTHONPATH='src'; python -m vassago_contract_runtime.cli check`;
`git diff --check`.
If clean, commit with
`feat(sc01): add nomad current-state review`.

## 2026-06-22 - PT-027.T17 Bridge Current-Path Review Sidecar

Goal:

- Stop insisting on the rejected Nomad default-root path and add a generic
  read-only bridge path router for current live-risk follow-up.

What was done:

- Added `src/vassago_contract_runtime/sc01_bridge_review.py`.
- Added CLI command `bridge-current-review`.
- Added `tests/design_runtime/test_sc01_bridge_review.py`.
- Wrote sidecars:
  - `12_current_state_review/sc01-bridge-current-review.json`;
  - `12_current_state_review/sc01-bridge-current-review.md`.
- Hardened Hyperlane fingerprinting so `function handle` alone does not create
  a protocol match.

Command:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli bridge-current-review --run runs/sc01-historical-6-v23-nomad-sidecars --target-id CT-05f41610b129
```

Observed:

```text
review_id=BCR-3ed18c3eb479
protocol_fingerprints=[nomad_replica]
active_path_count=4
ready_for_state_review_count=1
blocked_path_count=3
root_proof_verifier=candidate_ready_for_state_review
processed_message_replay=blocked_reader_missing
escrow_supply_delta=blocked_reader_missing
recipient_asset_moving=blocked_asset_delta_missing
current_live_risk=not_claimed
```

Decisions and reasoning:

- Bridge live-risk work should split by current path:
  endpoint/source validation, processed-message replay, root/proof verifier,
  escrow/supply delta and recipient asset-moving.
- The new sidecar is static/source/ABI triage. It does not execute Foundry, does
  not call write RPC methods and does not claim live exploitability.
- For Nomad current state, the only ready path is still root/proof state review;
  the already-run current-state probe rejected the historical default-root
  predicate.

Validation:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.design_runtime.test_sc01_bridge_review
python -m unittest discover -s tests
python -m vassago_contract_runtime.cli check
git diff --check
```

Observed:

```text
5 focused tests passed
94 full tests passed
check status=passed
git diff --check: only CRLF warning for cli.py
```

RESUME FROM HERE:

Commit this slice if desired, for example:
`feat(sc01): add bridge current path review`.
Then choose the next bridge path by sidecar status. For live-risk bridge work,
do not return to Nomad default-root; review another current path/protocol with
endpoint/source state, processed-message reader, root/proof state,
escrow/supply delta or recipient asset-moving evidence.

## 2026-06-22 - PT-028 Historical Exploit Corpus Seed

Goal:

- Stop depending on random target samples and build a benchmark-grade
  historical exploit corpus that can drive blind evaluation.

What was researched:

- `SunWeb3Sec/DeFiHackLabs` was cloned locally at commit `c496513`.
- The repo contained hundreds of Foundry reproduction PoCs; the first seed was
  curated from direct `src/test/*/*.sol` metadata.
- External expansion references were checked: DeFiHackLabs incident explorer,
  DeFiVulnLabs, MetaTrust SmartContractAttackPoC, Rekt and SlowMist Hacked.

What was implemented:

- Added `designs/historical-exploits/manifest.json`.
- Added `designs/historical-exploits/README.md`.
- Added `designs/historical-exploits/targets-blind-100.json`.
- Added `src/vassago_contract_runtime/historical_corpus.py`.
- Added CLI command:
  `python -m vassago_contract_runtime.cli historical-corpus-report`.
- Added `tests/design_runtime/test_historical_corpus.py`.

Corpus state:

```text
case_count=100
target_count=100
duplicate_target_count=0
invalid_cases=[]
sc01_access_control=20
bridge_message_auth=20
oracle_accounting=20
reentrancy_token=20
proxy_upgrade_signature=20
with_attack_tx=96
with_fork_block=90
with_vulnerable_contract=74
```

Validation:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli historical-corpus-report --targets-output designs/historical-exploits/targets-blind-100.json
python -m unittest tests.design_runtime.test_historical_corpus tests.design_runtime.test_sc01_bridge_review
```

Observed:

```text
historical-corpus-report status=completed
focused tests: 7 passed
```

Decisions:

- `blind_inputs` is the only part allowed during detector runs.
- `hidden_ground_truth` is scoring-only and must not drive detection logic.
- Historical metadata is not a live exploitability claim.
- PoC Solidity stays external; runtime corpus stores metadata and provenance.

Blockers:

- Full regression still needs to be rerun after this documentation/update
  slice.
- The blind benchmark itself has not been run yet.

RESUME FROM HERE:

Run:
`$env:PYTHONPATH='src'; python -m unittest discover -s tests`.
Then run:
`$env:PYTHONPATH='src'; python -m vassago_contract_runtime.cli check`.
Then run `git diff --check`. If clean, run the blind benchmark with
`designs/historical-exploits/targets-blind-100.json`. Do not read
`hidden_ground_truth` until scoring after the blind run.
