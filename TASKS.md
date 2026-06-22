# Tasks

This file is intentionally detailed. A fresh agent should be able to start from
here without reading the old Vassago conversation.

## Current Status

Repository bootstrap plus positive local SC01 runtime path complete.

PT-023.T01-T05, PT-024.T01-T12, PT-025.T01-T05, PT-025.T03B, PT-025.T04B
and PT-026.T01-T03 are implemented and covered by tests.
PT-024.T13-T18 are implemented: source-backed positive/negative verification,
normalized Slither IR-first semantic surface, real Slither Python API IR
extraction, local solc version selection and controlled compiler cache
provisioning via solc-select.
PT-025.T01B is implemented: phase 01 can resolve real ABI/source through the
read-only Etherscan V2 Explorer adapter when no `--source-fixture` is supplied.
PT-027.T01 first adversarial fixture slice is implemented: disabled
initializer, tx.origin authorization, open role-admin mutation and public
lifecycle noise.
PT-028.T01-T03 first historical exploit corpus seed is implemented: 100 blind
targets from DeFiHackLabs metadata, balanced across SC01, bridge/message-auth,
oracle/accounting, reentrancy/token and proxy/upgrade/signature.
PT-028.T05 post-run scorer is implemented as
`historical-corpus-score`.

## NEXT UP

1. `PT-028.T07` - analyze the blind score buckets:
   `67 candidate`, `32 none`, `1 runtime`, grouped by family and missing
   mapper.
2. `PT-028.T08` - turn the top missing mappers into design tasks:
   bridge paths, proxy/upgrade/signature, oracle/accounting and reentrancy/token.
3. `PT-028.T06` - expand corpus beyond 100 using DeFiHackLabs, DeFiVulnLabs,
   SmartContractAttackPoC, Rekt/SlowMist incident lists and manually verified
   addresses.
4. `PT-024.T19` - add per-target Slither/source failure summary if the blind
   benchmark shows repeated compile/import misses.

---

# PT-023 - Design Runtime Foundation

## Summary

Create the generic runtime that runs Designs against ContractTargets.

## PT-023.T01 - Core Models

Status: done, 2026-06-21.

Files:

- `src/vassago_contract_runtime/design_runtime/models.py`
- `tests/design_runtime/test_models.py`

Implement:

- `ContractTarget`
- `DesignSpec`
- `PhaseSpec`
- `GateSpec`
- `ArtifactSpec`
- `RunOptions`
- `PhaseStatus`
- `EvidenceStatus`

Mini tasks:

- `M01`: define dataclasses.
- `M02`: add JSON serialization.
- `M03`: add validation errors with stable codes.
- `M04`: add target id: `CT-<hash(chain|address)>`.
- `M05`: add phase id validation: `00_intake`, `01_dossier`, etc.

Acceptance:

- invalid address rejected;
- invalid phase id rejected;
- JSON roundtrip works;
- unit tests pass.

Result:

- Added `src/vassago_contract_runtime/design_runtime/models.py`.
- Added `tests/design_runtime/test_models.py`.
- Stable validation codes implemented.
- `ContractTarget.target_id` uses `CT-<hash(chain|address)>`.

## PT-023.T02 - Run Manifest And Artifact Index

Status: done, 2026-06-21.

Files:

- `src/vassago_contract_runtime/design_runtime/manifest.py`
- `src/vassago_contract_runtime/artifacts/store.py`
- `tests/design_runtime/test_manifest.py`

Implement:

- `run-manifest.json`;
- `target-manifest.json`;
- `phase-manifest.json`;
- artifact URI:
  `vassago://runs/{run_id}/targets/{target_id}/phases/{phase_id}/{artifact}`;
- content hash.

Mini tasks:

- `M01`: create run directory.
- `M02`: write initial manifest.
- `M03`: update phase status atomically.
- `M04`: index artifacts.
- `M05`: read artifact by URI.
- `M06`: block path traversal.

Acceptance:

- resume can load manifest;
- artifact hash is stable;
- path traversal test fails closed.

Result:

- Added `src/vassago_contract_runtime/design_runtime/manifest.py`.
- Added `src/vassago_contract_runtime/artifacts/store.py`.
- Added `tests/design_runtime/test_manifest.py`.
- Artifact URI format implemented:
  `vassago://runs/{run_id}/targets/{target_id}/phases/{phase_id}/{artifact}`.

## PT-023.T03 - Phase Runner With Resume

Status: done, 2026-06-21.

Files:

- `src/vassago_contract_runtime/design_runtime/runner.py`
- `tests/design_runtime/test_runner.py`

Implement:

- `run_design`;
- `resume_design`;
- `run_phase`;
- skip completed phases;
- stop on failed required phase;
- continue on optional phase failure when configured.

Mini tasks:

- `M01`: phase adapter protocol.
- `M02`: in-memory fake adapter.
- `M03`: run all phases.
- `M04`: resume after partial run.
- `M05`: stable stop reasons.

Acceptance:

- fake design with 3 phases runs;
- resume skips phase 1 and runs phase 2;
- failed phase writes error status.

Result:

- Added `src/vassago_contract_runtime/design_runtime/runner.py`.
- Added `tests/design_runtime/test_runner.py`.
- Runner supports required failure stop, optional failure continuation and resume skip.

## PT-023.T04 - CLI Skeleton

Status: done, 2026-06-21.

Files:

- `src/vassago_contract_runtime/cli.py`
- `tests/design_runtime/test_cli.py`

Commands:

- `check`
- `run-design`
- `resume`
- `artifact-read`

Acceptance:

- `python -m vassago_contract_runtime.cli check` exits 0.
- `run-design --dry-run` writes manifest.

Result:

- Added `src/vassago_contract_runtime/cli.py`.
- Implemented `check`, `run-design`, `resume`, and `artifact-read`.
- `run-design` and `resume` currently require `--dry-run` until real phase
  adapters exist.

## PT-023.T05 - Strict Check

Status: done, 2026-06-21.

Implement checks:

- design yaml valid;
- no production Python file > 800 lines;
- no forbidden evidence promotion strings outside gate module;
- no secrets in tracked docs;
- no artifact path traversal.

Result:

- Added `src/vassago_contract_runtime/quality.py`.
- `check` validates SC01 design YAML, Python line limit, evidence string
  placement, basic secret patterns and artifact path traversal behavior.

---

# PT-024 - SC01 Access Control Design

## Summary

Implement the first contract-first Design.

## PT-024.T01 - Design Spec

Status: done, 2026-06-21.

Files:

- `designs/sc01-access/design.yaml`
- `tests/design_runtime/test_sc01_design_spec.py`

Acceptance:

- design loads;
- phase graph is ordered;
- required artifacts are declared.

Result:

- Added `src/vassago_contract_runtime/design_runtime/design_loader.py`.
- `designs/sc01-access/design.yaml` loads into `DesignSpec`.
- Current phase count: 11.

## PT-024.T02 - Phase 00 Intake

Status: done, 2026-06-21.

Inputs:

- target list JSON.

Outputs:

- `target-manifest.json`;
- `scope-policy.json`.

Rules:

- validate chain;
- validate address;
- normalize address;
- no RPC needed.

Result:

- Added `src/vassago_contract_runtime/phases/intake.py`.
- The adapter writes `target-manifest.json` and `scope-policy.json`.
- It is a real local adapter, not a dry-run artifact.

## PT-024.T03 - Phase 01 Dossier

Status: done, 2026-06-21, skeleton with fixture source support.

Purpose:

Resolve ABI/source/proxy/code/hash/balances/log hints.

Adapters:

- SourceResolver;
- Explorer;
- RPC read-only.

Outputs:

- `scan-dossier.json`;
- `function-index.json`;
- `protocol-fingerprint.json`;
- `source-manifest.json`;
- `compile-context.json`.

Result:

- Added `src/vassago_contract_runtime/phases/dossier.py`.
- Added `NullSourceResolver` skeleton through PT-025.T01.
- Dossier status remains `skeleton`; with `--source-fixture` it indexes local
  ABI/source, but still does not run Explorer, Slither or source-truth.
- No network/RPC/Explorer/Slither/Foundry is used.

## PT-024.T04 - Phase 02 Semantic Surface

Status: done, 2026-06-21, skeleton adapter.

Purpose:

Map contract callable surface by effect, not by name.

Outputs:

- `access-surface.json`;
- `semantic-map.json`;
- `guard-map.json`;
- `state-write-map.json`;
- `role-graph.json`.

Rules:

- ABI is inventory only.
- Source/IR/storage/events drive semantics.
- Regex fallback is low confidence.

Result:

- Added `src/vassago_contract_runtime/phases/semantic_surface.py`.
- Reads phase 01 `function-index.json` and `source-manifest.json`.
- Writes `access-surface.json`, `semantic-map.json`, `guard-map.json`,
  `state-write-map.json` and `role-graph.json`.
- Output is static/candidate-only; source-truth must validate every claim.

## PT-024.T05 - Phase 03 Corpus Motifs

Status: done, 2026-06-21, skeleton adapter.

Purpose:

Use SC01 corpus records as hypothesis generators.

Outputs:

- `sc01-corpus-matches.json`;
- `sc01-thesis-candidates.json`.

Rules:

- corpus match is not evidence;
- each match must list negative signals.

Result:

- Added `src/vassago_contract_runtime/phases/corpus_motifs.py`.
- Reads phase 01 `function-index.json`, `source-manifest.json` and
  `protocol-fingerprint.json`.
- Writes `sc01-corpus-matches.json`.
- Writes `sc01-thesis-candidates.json`.
- Status is `candidate_only` or `no_matches`; no source-truth, RPC or Foundry.

## PT-024.T06 - Phase 04 Thesis Acquisition

Status: done, 2026-06-21, skeleton adapter.

Purpose:

Choose high-signal SC01 theses.

Initial theses:

- `uninitialized_implementation_proxy`;
- `uups_weak_auth`;
- `safe_module_fallback`;
- `erc4337_kernel_validator`;
- `bridge_endpoint_source_validation`;
- `role_admin_self_escalation`;
- `hook_callback_caller_validation`;
- `arbitrary_sender_or_from`.

Outputs:

- `sc01-thesis-queue.json`;
- `sc01-acquisition-report.json`.

Result:

- Added `src/vassago_contract_runtime/phases/thesis_acquisition.py`.
- Reads phase 03 thesis candidates plus phase 02 semantic/guard maps.
- Writes a source-truth queue with `queued_for_source_truth` items.
- Does not verify source truth, read chain state or enable Foundry.

## PT-024.T07 - Phase 05 Source Truth

Status: done, 2026-06-21, skeleton adapter.

Purpose:

Reject false positives before state/runtime.

Must answer:

- is there a real storage write?
- is the state critical?
- is the guard really weaker?
- is the actor public by design?
- is this lifecycle/accounting normal?

Outputs:

- `sc01-source-truth.json`.

Result:

- Added `src/vassago_contract_runtime/phases/source_truth.py`.
- Reads thesis queue, access surface, guard map and state-write map.
- Writes source-truth review records with `source_truth_verified=false`.
- Keeps status `blocked`; no runtime gate is opened.

Statuses:

- `source_truth_verified`;
- `source_truth_rejected`;
- `source_truth_blocked`.

## PT-024.T08 - Phase 06 On-Chain State

Status: done, 2026-06-21, skeleton adapter.

Purpose:

Read only the state needed by verified/blocking theses.

Outputs may include:

- `admin-state.json`;
- `proxy-state.json`;
- `safe-state.json`;
- `role-state.json`;
- `bridge-state.json`;
- `aa-state.json`.

Rules:

- read-only RPC;
- chunk logs;
- redact RPC URLs;
- persist block window.

Result:

- Added `src/vassago_contract_runtime/phases/onchain_state.py`.
- Writes `admin-state.json`, `proxy-state.json` and `role-state.json`.
- Bootstrap mode does not call RPC; status stays `needs_provider`.

## PT-024.T09 - Phase 07 Proof Pieces

Status: done, 2026-06-21.

Purpose:

Decide whether compile/runtime can proceed.

Required pieces:

- source truth guard gap;
- actor model;
- codable args;
- measurable reader;
- measurable delta;
- explicit predicate.

Outputs:

- `sc01-proof-piece-state.json`;
- `sc01-exploit-hypotheses.json`;
- `sc01-runtime-ready.json`.

## PT-024.T10 - Phase 08 Compile-Only

Status: done, 2026-06-21.

Purpose:

Generate and compile Foundry harness without executing exploit runtime.

Outputs:

- `VassagoSC01Harness.t.sol`;
- `compile-result.json`.

Statuses:

- `compile_only_passed`;
- `compile_failed`;
- `compile_skipped_not_ready`.

## PT-024.T11 - Phase 09 Runtime Foundry Local

Status: done, 2026-06-21.

Purpose:

Run local fork only when runtime-ready.

Rules:

- no broadcast;
- no private key;
- no live transaction;
- local/fork only;
- fixed block where possible.
- explicit `--runtime-authorized` required.

Outputs:

- `foundry-runtime-result.json`;
- `assertion-result.json`;
- `evidence.md`.

Statuses:

- `runtime_completed`;
- `blocked_runtime_authorization_required`;
- `not_reproduced`;
- `runtime_failed`;
- `inconclusive`.

Result:

- Added `src/vassago_contract_runtime/phases/runtime_foundry.py`.
- Runtime uses `SubprocessFoundryAdapter.run_local_fork()`.
- Local positive fixture passed `forge test --match-contract VassagoSC01Harness`.
- No broadcast command is generated.

## PT-024.T12 - Phase 10 Final Report

Status: done, 2026-06-21.

Outputs:

- `sc01-final-report.json`;
- `sc01-final-report.md`.

Report must include:

- what was tested;
- what was rejected;
- what was blocked;
- exact evidence level;
- commands to reproduce local evidence;
- no overclaim.

---

# PT-025 - Adapter Interfaces

## PT-025.T01 - SourceResolver Adapter

Status: done, 2026-06-21, interface plus null, local fixture and Explorer-backed adapters.

Interface:

- `resolve(target)`.

Must support:

- Etherscan-compatible APIs;
- Sourcify;
- local fixture.

Result:

- Added `src/vassago_contract_runtime/contracts/source_resolver.py`.
- Added `src/vassago_contract_runtime/contracts/target.py`.
- Implemented `SourceResolver` protocol, `SourceResolution`, `NullSourceResolver`
  `FixtureSourceResolver` and `ExplorerSourceResolver`.
- Local fixture source input is supported through `--source-fixture`.
- When no `--source-fixture` is supplied, bootstrap mode uses
  `ExplorerSourceResolver(EtherscanV2ExplorerAdapter(...))`.
- Default cache path is `<run>/_cache/etherscan-v2`; override with
  `--source-cache-dir`.
- Sourcify provider adapter is still future work.

## PT-025.T01B - Explorer-backed SourceResolver wiring

Status: done, 2026-06-21.

Implemented:

- `ExplorerSourceResolver` bridges `ExplorerContractContext` to
  `SourceResolution`;
- `runtime_api.adapters_for()` now chooses:
  - `FixtureSourceResolver` when `--source-fixture` is supplied;
  - Etherscan V2 read-only Explorer source resolver otherwise;
- CLI and MCP/tool payloads accept `source_cache_dir`;
- if `ETHERSCAN_API_KEY` is missing, the resolver returns structured
  unresolved state instead of falling back to fake data.

Validation:

- fake Explorer mapping test;
- runtime wiring test confirms no-fixture bootstrap uses Explorer resolver and
  cache path;
- no live API smoke was run in this session because `ETHERSCAN_API_KEY` was not
  set in the shell.

## PT-025.T02 - Explorer Adapter

Status: done, 2026-06-21, interface plus null and Etherscan V2 read-only cache adapter.

Interface:

- `get_contract_context(target)`.
- `get_logs(target, from_block, to_block, topics)`.

Result:

- Added `src/vassago_contract_runtime/explorer/adapter.py`.
- Implemented `ExplorerAdapter`, `ExplorerContractContext`,
  `ExplorerLogsResult`, `NullExplorerAdapter` and
  `EtherscanV2ExplorerAdapter`.
- Etherscan V2 adapter is read-only, uses `chainid`, supports filesystem cache
  and never stores the API key in cache keys.
- Sourcify and richer Explorer endpoints are still future work.

## PT-025.T03 - Slither Adapter

Status: done, 2026-06-21, interface plus null and subprocess adapter.

Interface:

- `analyze(input)`.

Result:

- Added `src/vassago_contract_runtime/slither/adapter.py`.
- Implemented `SlitherAdapter`, `SlitherInput`, `SlitherAnalysisResult` and
  `NullSlitherAdapter`.
- Implemented `SubprocessSlitherAdapter` using `slither <source> --json <file>`.
- Python API integration is still future work.

## PT-025.T04 - Foundry Adapter

Status: done, 2026-06-21, interface plus null adapter.

Interface:

- `compile_harness`;
- `run_local_fork`.

Must enforce no broadcast.

Result:

- Added `src/vassago_contract_runtime/foundry/adapter.py`.
- Implemented `FoundryAdapter`, `FoundryHarnessInput`,
  `FoundryRunResult` and `NullFoundryAdapter`.
- Real `forge` subprocess execution is future `PT-025.T04B`.

## PT-025.T05 - Corpus Adapter

Status: done, 2026-06-21, interface plus local design corpus adapter.

Interface:

- `scan(context)`.

Result:

- Added `src/vassago_contract_runtime/corpus/adapter.py`.
- Implemented `CorpusAdapter`, `CorpusScanContext`, `CorpusScanResult`,
  `NullCorpusAdapter` and `DesignCorpusAdapter`.
- Reads local `designs/<design>/corpus/*.yaml`.
- Produces candidate-only routing hints, never evidence.

# PT-026 - Agent And MCP

## PT-026.T01 - Tool Contracts

Status: done 2026-06-21.

Tools:

- `vassago_design_run`;
- `vassago_design_resume`;
- `vassago_artifact_read`.

Implemented:

- `src/vassago_contract_runtime/tools/contracts.py`;
- `src/vassago_contract_runtime/tools/runtime_tools.py`;
- `src/vassago_contract_runtime/runtime_api.py`;
- `tests/design_runtime/test_tool_contracts.py`.

Current behavior:

- exposes campaign-level contracts only, not fine-grained phase internals;
- invokes the same runtime path as the CLI;
- supports aliases `run_design`, `resume_design` and `artifact_read`;
- keeps local-only/no-broadcast/no-shell policy in each contract.

## PT-026.T02 - MCP stdio

Status: done 2026-06-21.

Local-only stdio first.

Implemented:

- `src/vassago_contract_runtime/mcp/server.py`;
- `src/vassago_contract_runtime/mcp/__init__.py`;
- CLI command `python -m vassago_contract_runtime.cli mcp --stdio`;
- `tests/design_runtime/test_mcp_server.py`.

Exposed methods:

- `initialize`;
- `notifications/initialized`;
- `ping`;
- `tools/list`;
- `tools/call`.

Exposed tools:

- `vassago_design_run`;
- `vassago_design_resume`;
- `vassago_artifact_read`.

Current behavior:

- newline-delimited JSON-RPC over stdin/stdout;
- stdout contains only MCP JSON-RPC messages;
- no shell tool, no broadcast tool, no phase-internal tools.

## PT-026.T03 - Hermes Skill

Status: done 2026-06-21.

Skill:

- `vassago-sc01-design`.

Prompt behavior:

- call `vassago_design_run`;
- read report;
- only request subagent when a phase is blocked;
- never call fine-grained tools first.

Implemented:

- installed local Hermes skill at:
  `C:\Users\PC\AppData\Local\hermes\skills\domain\vassago-sc01-design\SKILL.md`;
- versioned prompt source at
  `designs/sc01-access/prompts/vassago-sc01-design.md`;
- configured Hermes MCP server `vassago_contract_runtime`;
- wrapper command:
  `scripts/hermes-vassago-contract-runtime-mcp.cmd`.

Validation:

- `hermes skills list` shows `vassago-sc01-design` enabled;
- `hermes mcp test vassago_contract_runtime` connects and discovers 3 tools.

---

# PT-027 - Validation Campaigns

## PT-027.T01 - Local Fixtures

Status: done first slice, 2026-06-21.

Implemented:

- `tests/fixtures/targets_adversarial.json`;
- `tests/fixtures/source_fixture_adversarial.json`;
- `designs/sc01-access/corpus/tx-origin-auth.yaml`;
- `designs/sc01-access/corpus/role-admin-escalation.yaml`;
- `designs/sc01-access/corpus/public-lifecycle-noise.yaml`;
- regression test
  `BootstrapPhaseTests.test_adversarial_fixture_suite_routes_without_false_foundry_promotion`.

Covered cases:

- disabled initializer with `_disableInitializers()` is not promoted;
- `tx.origin` authorization is routed as a thesis/guard signal but remains
  non-Foundry until proof pieces exist;
- open role-admin/operator mutation is routed as a thesis but remains blocked;
- public lifecycle function `settleRound()` is rejected as `public_lifecycle`.

Remaining fixture expansion:

- missing critical guard;
- safe public deposit;
- no-op guard;
- post-check modifier;
- Safe module;
- bridge endpoint/source validation;
- ERC4337 validator;
- role self-admin with role graph.

## PT-027.T01B - Local Fixtures Expansion

Status: pending.

Add the remaining adversarial/metamorphic cases listed above. Keep each case
local-only and assert that `foundry_allowed` changes only when all proof pieces
are complete.

## PT-027.T02 - SC01 Smoke 5 Contracts

Status: done first real smoke, 2026-06-21.

Run design on 5 known contracts.

Acceptance:

- no crash. Done after regex fix.
- phase report complete. Done: all 5 targets completed 11 phases.
- no false reproduced evidence. Done: all final reports are
  `blocked_no_runtime_ready`, `foundry_allowed=false`.

Targets:

- ETH USDC FiatTokenProxy;
- ETH ERC-4337 EntryPoint v0.6;
- ETH Safe Singleton 1.3.0;
- Base Uniswap v4 PoolManager;
- BSC PancakeSwap MasterChefV2.

Results:

- source resolution via Etherscan V2 worked for all 5;
- Slither Python completed for 4/5;
- USDC Slither failed with `solc_version_cache_missing` for `0.4.24`;
- source truth stayed `blocked` for all 5, with no runtime evidence promoted.

Bug fixed during smoke:

- `sc01_source._is_user_funded_accounting()` had an invalid regex branch for
  plain assignment paths. Fixed and covered by
  `test_public_normal_behavior_handles_plain_assignment_without_regex_error`.

## PT-027.T02B - Curated 5 With Compiler Provisioning

Status: pending.

Run the same curated set with explicit `--allow-solc-install` if we want USDC's
Solidity `0.4.24` source to be Slither-analyzed locally.

Do not make this default. It is a setup/smoke action only.

## PT-027.T03 - SC01 Smoke 20 Curated Contracts

Status: pending.

Acceptance:

- resume works;
- blocked reasons cluster cleanly;
- compile-only runs only when ready.

## PT-027.T04 - Larger Batch

Status: blocked.

Only after PT-027.T03.

---

---

# PT-024.T09 - Proof pieces skeleton

Status: done 2026-06-21.

Implemented:

- `src/vassago_contract_runtime/phases/proof_pieces.py`;
- `sc01-proof-piece-state.json`;
- `sc01-exploit-hypotheses.json`;
- `sc01-runtime-ready.json`.

Current behavior:

- consolidates source-truth and on-chain state blockers;
- sets `foundry_allowed=false` when proof pieces are incomplete;
- never calls Foundry and never promotes evidence.

# PT-024.T10 - Compile-only skeleton

Status: done 2026-06-21.

Implemented:

- `src/vassago_contract_runtime/phases/compile_only.py`;
- `VassagoSC01Harness.t.sol`;
- `compile-result.json`.

Current behavior:

- writes a harmless sentinel harness;
- skips Foundry when `compile_ready_count=0`;
- calls the Foundry adapter only when compile-ready hypotheses exist.

# PT-024.T12 - Final report skeleton

Status: done 2026-06-21.

Implemented:

- `src/vassago_contract_runtime/phases/final_report.py`;
- `sc01-final-report.json`;
- `sc01-final-report.md`.

Current behavior:

- reports `blocked_no_runtime_ready` for current fixture bootstrap;
- records no-broadcast policy and next required proof pieces.

# PT-025.T04B - Foundry subprocess adapter

Status: done 2026-06-21.

Implemented:

- `SubprocessFoundryAdapter` in `src/vassago_contract_runtime/foundry/adapter.py`.

Current behavior:

- `compile_harness()` runs local `forge build` in an ephemeral workspace;
- `run_local_fork()` runs local `forge test` only when
  `runtime_ready=true` and `runtime_authorized=true`;
- no broadcast command is generated.

# RESUME FROM HERE

Start with `PT-024.T13`. Current bootstrap runs phases 00 through 10, including
local Foundry runtime when `foundry_allowed=true` and `--runtime-authorized` is
explicitly passed. The positive UUPS fixture already reaches
`runtime_completed`; keep it as regression while replacing the metadata shortcut
with source/IR-backed verification.

## PT-024.T13 - Source-backed positive verification

Status: done, 2026-06-21.

Replace the current local-positive fixture shortcut with a source-backed verifier
for uninitialized implementation/UUPS initializer cases.

Acceptance:

- verifies `initialize()` writability from source/IR, not fixture metadata alone;
- verifies no `_disableInitializers()`;
- verifies `owner()` or equivalent reader;
- keeps live contracts blocked without proxy/state impact evidence;
- preserves the local positive fixture as a regression test.

Result:

- Added `src/vassago_contract_runtime/sc01_source.py`.
- `source_truth.py` now verifies the positive initializer path from source:
  `initialize()`, admin write, missing `_disableInitializers()`, admin reader
  and upgrade sink.
- `source_fixture_positive.json` no longer uses `local_positive_sc01_case`.
- `onchain_state.py` only clears local state blockers for fixture provider
  plus source-backed verification; live contracts still need proxy/state
  sidecars.
- `compile_only.py` renders the initializer harness from source-backed
  verification instead of metadata.

## PT-024.T14 - Source-backed negative verification

Status: done, 2026-06-21.

Add negative source-truth policies for safe public lifecycle/accounting paths so
SC01 does not promote public deposits, fee accrual, keeper actions or protocol
lifecycle transitions into access-control proof pieces.

Result:

- Added `evaluate_public_normal_behavior()` in
  `src/vassago_contract_runtime/sc01_source.py`.
- Added negative fixture:
  `tests/fixtures/source_fixture_negative.json` and
  `tests/fixtures/targets_negative.json`.
- Source-truth now emits `source_truth_rejected` when all candidates are
  rejected by source-backed negative policy.
- Anti-hardcode case `initializeMarket()` is rejected as
  `caller_funded_accounting`, despite matching the `initialize` motif.
- Foundry remains blocked for rejected candidates.

## PT-024.T15 - Slither IR source extraction

Status: done, 2026-06-21.

Use Slither subprocess/Python IR outputs as the primary source for function
bodies, writes, modifiers and calls when compile context is available.

Result:

- `compile-context.json` now becomes `status=available` when the source bundle
  exists, including selected source file and target contract metadata.
- `SemanticSurfaceAdapter` accepts a `SlitherAdapter` and consumes normalized
  `ir.functions[]` as primary extraction.
- `access-surface.json` now records `slither` summary and per-function
  `extraction_source`.
- If Slither IR is unavailable or no adapter is configured, phase 02 falls back
  to the previous ABI/source heuristic and records the degraded source.
- Tests prove that, with compile context and Slither IR, state writes and guard
  signals come from `slither_ir` instead of the heuristic parser.

Limit:

- The current `SubprocessSlitherAdapter` invokes Slither CLI JSON, which is
  detector output, not full SlithIR. Full real IR extraction is tracked as
  `PT-024.T16`.

## PT-024.T16 - Real Slither Python API IR extraction

Status: done, 2026-06-21.

Use Slither Python API when installed to populate the normalized IR contract
with function modifiers, state reads/writes, calls, inheritance and source refs.
Keep CLI detector JSON as auxiliary detector context, not as proof of writes.

Result:

- Added `PythonSlitherAdapter` in
  `src/vassago_contract_runtime/slither/adapter.py`.
- The adapter imports `slither.slither.Slither` optionally and returns
  `status=unavailable` when the package is not installed.
- It writes source bundles into an ephemeral workspace, runs Slither from that
  workspace for Windows path compatibility, and normalizes:
  - contract names and inheritance;
  - function signatures, visibility and mutability;
  - modifiers;
  - state reads/writes;
  - variables read/written;
  - internal/external calls;
  - condition expressions;
  - SlithIR operation strings;
  - source excerpts and source mapping.
- `runtime_api.py` now wires `SemanticSurfaceAdapter(PythonSlitherAdapter())`
  in bootstrap mode.
- Local fixtures use compiler-compatible pragma `^0.8.0` so the installed
  Slither/solc path can exercise real IR.
- `pyproject.toml` exposes optional dependency group:
  `pip install .[slither]`.

Validation:

- Real Slither Python smoke on `tests/fixtures/source_fixture_positive.json`
  produced `slither.status=completed`, `provider=slither_python`,
  `ir_status=completed`, `initialize().extraction_source=slither_ir`,
  `state_write_signals=["owner"]`, and final `runtime_completed`.
- Real Slither Python smoke on the negative fixture produced
  `initializeMarket().extraction_source=slither_ir`,
  `state_write_signals=["balances", "totalDeposits"]`, and remained
  `source_truth_rejected`.

Limit:

- Real contracts can still fail Slither when source pragma/compiler version does
  not match the local solc. This is tracked as `PT-024.T17`.

## PT-024.T17 - Slither compiler/version selection

Status: done, 2026-06-21.

Use compile context to select or provision the correct solc for Slither Python
runs. Until this exists, incompatible pragmas produce a structured
`slither_python_analysis_failed` error and phase 02 falls back to heuristic
extraction.

Result:

- `compile-context.json` now records:
  - `compiler_version`;
  - Solidity `pragma_constraints`;
  - `solc_version_selection.requested_version`;
  - selection source (`compiler_metadata` or `pragma_constraint`).
- `PythonSlitherAdapter` reads `solc_version_selection` and sets
  `SOLC_VERSION` while Slither Python runs.
- The adapter records compiler metadata in `access-surface.json.slither`:
  - requested version;
  - current detected `solc --version`;
  - selection status;
  - env var used.
- Environment variables and working directory are restored after Slither runs.
- If Slither cannot compile, the error remains structured and phase 02 falls
  back to heuristic extraction.

Validation:

- Positive fixture smoke produced:
  `compiler_selection.status=current_matches_requested`,
  `requested_version=0.8.20`, `current_solc_version=0.8.20`,
  `initialize().extraction_source=slither_ir`, and final
  `runtime_completed`.
- Negative fixture smoke produced:
  `initializeMarket().extraction_source=slither_ir`,
  `state_write_signals=["balances", "totalDeposits"]`,
  `source_truth_rejected`, and `foundry_allowed=false`.

Limit:

- T17 selects/uses installed compiler versions. It does not download or
  provision missing solc versions. If real targets need missing versions,
  implement `PT-024.T18`.

## PT-024.T18 - Slither compiler cache/provisioning

Status: done, 2026-06-21.

Add a controlled compiler cache/provisioning strategy for missing solc versions.
Do this only after curated real-contract smoke quantifies compiler misses.

Result:

- Added `src/vassago_contract_runtime/slither/solc_manager.py`.
- Added `SolcSelectManager`, which:
  - lists installed versions with `solc-select versions`;
  - reports `compiler_cache_missing` without installing by default;
  - installs with `solc-select install <version>` only when explicitly allowed;
  - never calls `solc-select use`;
  - leaves per-run version selection to `SOLC_VERSION`.
- `PythonSlitherAdapter` now uses the manager before invoking Slither.
- Missing compiler versions fail fast with structured
  `solc_version_cache_missing`, allowing phase 02 fallback.
- CLI/tool payload now supports explicit `allow_solc_install`.
- `access-surface.json.slither.compiler_selection.provisioning` records cache
  status, installed versions, manager, install attempt and errors.

Validation:

- Unit tests cover cache miss without install, install only when allowed, env
  restoration and Slither skip when requested compiler is missing.
- Positive smoke `runs/sc01-positive-t18` completed with
  `provisioning.status=current_matches_requested`, `install_attempted=false`,
  `slither_ir`, and final `runtime_completed`.
- Negative smoke `runs/sc01-negative-t18` completed with Slither IR and stayed
  `source_truth_rejected`, `foundry_allowed=false`.

Limit:

- `allow_solc_install` can download compiler binaries through solc-select. Keep
  it off for deterministic/offline runs and only enable it in a controlled
  setup step or explicit provider smoke.

## PT-024.T19 - Slither failure summary by target

Status: planned if needed.

Aggregate Slither compiler/import failures across a curated real-contract run
so we can decide whether misses come from compiler cache, missing imports,
unsupported source bundles or real parser failures.

## PT-027.T02 - SC01 smoke 5 curated real contracts

Status: done, 2026-06-21.

Run five curated real contracts with real Etherscan V2 source resolution,
compile-context generation and Slither Python IR:

- ETH EntryPoint v0.6;
- BSC PancakeSwap MasterChefV2;
- Base Uniswap v4 PoolManager;
- ETH Safe Singleton 1.3.0;
- ETH USDC FiatTokenProxy.

Fixes made during the smoke:

- `ExplorerSourceResolver` now adapts Etherscan V2 contract context into the
  phase 01 `SourceResolver` contract.
- CLI/tool payload supports `--source-cache-dir`.
- Flat Etherscan source names without `.sol` are normalized before writing
  source bundles.
- `compile-context.json.selected_source_file` now selects the source declaring
  `metadata.contract_name`, not the first file alphabetically.
- `compile-context.json.solc_remaps` now infers Foundry-style `lib/<pkg>`
  remappings such as `solmate/=lib/v4-core/lib/solmate/`.
- Source-truth regex no longer crashes on plain assignment patterns.

Final real smoke:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets-curated-real-5.json --output runs/sc01-curated-real-5-v4 --bootstrap-adapters
```

Result:

- `executed_count=55`;
- `failed_count=0`;
- all 5 `source-manifest.json` files resolved through `etherscan_v2`;
- all 5 `access-surface.json.slither.status=completed`;
- selected source files:
  - `contracts/core/EntryPoint.sol`;
  - `contracts/MasterChefV2.sol`;
  - `lib/v4-core/src/PoolManager.sol`;
  - `contracts/GnosisSafe.sol`;
  - `FiatTokenProxy.sol`;
- all 5 final reports are `blocked_no_runtime_ready`;
- all 5 have `foundry_allowed=false`.

Limit:

- This proves the read-only source/compile/Slither path works for the curated
  sample. It does not prove an SC01 vulnerability. Foundry runtime remains
  gated until source truth, actor, args, reader, delta and predicate are all
  complete.

## PT-027.T03 - SC01 smoke 20 curated real contracts

Status: done, 2026-06-21.

Run twenty curated ETH/BSC/Base contracts through the real read-only bootstrap
pipeline after mapper/source-truth hardening.

Command:

```powershell
$envFile='C:\Users\PC\Desktop\Vassago\.env'
# loaded ETHERSCAN_API_KEY into process without printing it
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets-curated-real-20.json --output runs/sc01-curated-real-20-v8 --bootstrap-adapters --allow-solc-install
```

Result:

- `executed_count=220`;
- `failed_count=0`;
- all 20 source bundles resolved through `etherscan_v2`;
- all 20 Slither Python runs completed;
- 13 SC01 thesis candidates reached source-truth review;
- all 13 were rejected by source-backed negative policy;
- all 20 final reports are `blocked_no_runtime_ready`;
- all 20 have `foundry_allowed=false`;
- `runtime_ready_total=0`.

Implemented during the 20-contract smoke:

- phase 03 now emits thesis candidates only when there is function-level
  evidence from `access-surface.json`, instead of global source text matches;
- source-truth rejects common non-SC01 patterns:
  - transparent proxy admin upgrade paths;
  - initialized EIP-1967 proxies with live implementation context;
  - protocol pool initializers;
  - public factory/pool creation;
  - token/operator approval APIs;
  - caller-funded accounting/lifecycle/operator behavior;
- Etherscan standard JSON absolute source unit names are normalized;
- compile context remapping inference covers Uniswap/OpenZeppelin nested
  package layouts seen in the curated sample.

Interpretation:

- This is a pipeline-quality result, not vulnerability evidence.
- The correct behavior for this curated sample is terminal rejection of broad
  false candidates and no Foundry runtime.

## PT-027.T04 - next high-signal acquisition

Status: done, 2026-06-22.

Use the 20-contract smoke result to avoid random expansion. The next useful
step is acquiring targets with stronger SC01 signal:

- UUPS implementations with source-backed weak or ambiguous `_authorizeUpgrade`;
- proxies where implementation state impact can be proven from chain state;
- role-admin graphs with real role reader/effect;
- Safe/AA/module targets with initialized state sidecars and measurable
  deltas.

## PT-027.T05 - SC01 historical curated targets

Status: done, 2026-06-21.

Add six historical SC01-adjacent targets and run them through the real
Explorer/source/Slither/design flow:

```text
tests/fixtures/targets-sc01-historical-6.json
runs/sc01-historical-6-v4-runtime
```

Targets:

- BadgerDAO `WarRoomGatedProxy`;
- Audius `AudiusAdminUpgradeabilityProxy`;
- Nomad `UpgradeBeaconProxy` / Replica context;
- Furucombo `Proxy`;
- Alchemix `AlchemixHarvester`;
- Wormhole `Wormhole`.

Implemented during this slice:

- source-backed AccessControl initializer verifier:
  `_setupRole(DEFAULT_ADMIN_ROLE, ...)` inside external/public `initialize`;
- codable initializer args for `address` and `address[]`;
- local readiness for verified initializer patterns without claiming live
  chain impact;
- AccessControl Foundry harness that asserts
  `hasRole(DEFAULT_ADMIN_ROLE, caller)`;
- runtime assertion wording now comes from `sc01-source-truth.json`, not fixed
  `owner()` text.

Validated command:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets-sc01-historical-6.json --output runs/sc01-historical-6-v4-runtime --bootstrap-adapters --allow-solc-install --runtime-authorized
```

Result:

- `executed_count=66`;
- `failed_count=0`;
- `source_resolved=6/6`;
- `slither_completed=5/6`;
- `source_truth_verified_total=1`;
- `runtime_ready_total=1`;
- `foundry_allowed=1`;
- `compile_passed=1`;
- `runtime_completed=1`.

Concrete reproduced local evidence:

- BadgerDAO `WarRoomGatedProxy`;
- predicate: unauthorized caller invokes `initialize` and obtains
  `DEFAULT_ADMIN_ROLE`;
- measured delta:
  `hasRole(DEFAULT_ADMIN_ROLE, unauthorized caller)` changes false to true;
- evidence status: `runtime_local`;
- broadcast: no.

Current blockers for the other historical cases:

- Audius needs governance/proxy implementation-state mapper.
- Nomad needs bridge root/proof mapper and Slither failure triage.
- Furucombo needs delegatecall/proxy-storage mapper.
- Alchemix needs keeper/actor model and measurable state delta.
- Wormhole needs implementation initializer/UUPS context mapper.

## PT-027.T06 - Audius proxy storage collision base

Status: done, 2026-06-21.

Added a dedicated SC01 thesis for the Audius-style proxy storage collision /
reinitializer class:

```text
designs/sc01-access/corpus/proxy-storage-collision-reinitializer.yaml
runs/sc01-historical-6-v9-audius-privileged-writes-live
```

Implemented:

- `DossierAdapter` now resolves a related proxy implementation source when the
  Explorer source context exposes `proxy_context.implementation`;
- `evaluate_known_non_sc01_pattern()` rejects Audius `upgradeTo(address)` as
  `custom_proxy_admin_path`, so it is not misclassified as weak UUPS auth;
- `evaluate_proxy_storage_collision_reinitializer()` recognizes:
  - proxy-side `proxyAdmin` slot-zero storage;
  - fallback/delegatecall path;
  - Explorer proxy implementation context;
  - implementation source resolved as `Governance`;
  - implementation `Initializable` slot-zero flags;
  - `Governance.initialize(...)`;
  - privileged initializer writes with readers:
    `registry`, `votingPeriod`, `executionDelay`,
    `maxInProgressProposals`, `votingQuorumPercent`,
    `guardianAddress`.

Validated run:

```powershell
# loaded ETHERSCAN_API_KEY from C:\Users\PC\Desktop\Vassago\.env without printing it
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets-sc01-historical-6.json --output runs/sc01-historical-6-v9-audius-privileged-writes-live --bootstrap-adapters --allow-solc-install --runtime-authorized
```

Result:

- `executed_count=66`;
- `failed_count=0`;
- Audius source resolved through Etherscan V2;
- Audius implementation source resolved:
  `0x1c91af03a390b4c619b444425b3119e553b5b44b`, contract `Governance`;
- Audius UUPS thesis rejected as `custom_proxy_admin_path`;
- Audius proxy-storage-collision thesis status:
  `source_truth_blocked_proxy_side_verified`;
- remaining Audius blockers:
  - `proxy_delegatecall_initializer_calldata_required`;
  - `measurable_proxy_state_delta_required`;
- Audius `foundry_allowed=false`;
- Badger remains the only `runtime_local` reproduced case.

This is not an Audius reproduction and not a live impact claim. It is a
source-backed readiness improvement for the next mapper.

## PT-027.T07 - proxy collision runtime mapper

Status: done, 2026-06-21.

Implemented the Audius-style runtime mapper:

- added `src/vassago_contract_runtime/sc01_proxy_collision.py`;
- derives the exact delegated initializer plan for
  `initialize(address,uint256,uint256,uint256,uint16,address)`;
- uses bounded local arguments:
  `address(this), 3, 0, 1, 4, address(this)`;
- generates an interface-only Foundry harness that calls the historical
  Audius Governance proxy through fallback/delegatecall;
- measures proxy-side reader deltas:
  `getGuardianAddress()`, `getRegistryAddress()`,
  `getVotingPeriod()`, `getExecutionDelay()`,
  `getVotingQuorumPercent()`, `getMaxInProgressProposals()`;
- pins the fork at block `15201793`;
- redacts `--fork-url` in Foundry artifacts before writing JSON.

Validated run:

```powershell
# loaded ETHERSCAN_API_KEY and VASSAGO_FORK_RPC_* from C:\Users\PC\Desktop\Vassago\.env without printing values
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets-sc01-historical-6.json --output runs/sc01-historical-6-v11-audius-runtime --bootstrap-adapters --allow-solc-install --runtime-authorized
```

Audius result:

- artifact:
  `runs/sc01-historical-6-v11-audius-runtime/targets/CT-3f08e02c1bef`;
- `source_truth_verified_count=1`;
- `foundry_allowed=true`;
- `compile_status=compile_only_passed`;
- `runtime_status=runtime_completed`;
- `assertion-result.status=passed`;
- evidence status: `runtime_local`;
- broadcast: no;
- RPC URL token: not present in target artifacts.

This is historical fork/local evidence for Audius. It is not a current live
funds-at-risk claim.

## PT-027.T08 - Audius impact review sidecar

Status: done, 2026-06-21.

Implemented:

- added `src/vassago_contract_runtime/sc01_impact.py`;
- added CLI command:
  `python -m vassago_contract_runtime.cli impact-review --run <run> --target-id <target>`;
- writes:
  - `11_impact_review/sc01-impact-review.json`;
  - `11_impact_review/sc01-impact-review.md`.

Validated artifact:

```text
runs/sc01-historical-6-v11-audius-runtime/targets/CT-3f08e02c1bef/phases/11_impact_review/sc01-impact-review.json
```

Audius impact review result:

- `verdict=historical_reproduced_critical`;
- `historical_impact.severity=critical_historical`;
- `local_reproduction.status=runtime_completed`;
- `local_reproduction.assertion_status=passed`;
- `current_live_risk.status=not_claimed`;
- `no_broadcast=true`.

Decision:

- Audius can be discussed as historical reproduced critical.
- Do not claim current live high/critical severity without a fresh current-state
  review of patched deployments, proxy state, token balances and permissions.

## PT-027.T09 - Wormhole implementation/UUPS context blocker

Status: done first slice, 2026-06-21.

Implemented:

- `DossierAdapter` now indexes functions/events from
  `related_sources.implementation` with:
  - `source_relation=proxy_implementation`;
  - `execution_context=proxy_delegatecall`.
- `SemanticSurfaceAdapter` now finds function bodies in related implementation
  sources.
- SC01 source recognizers now evaluate effective proxy + implementation
  ABI/source.
- added `evaluate_wormhole_uninitialized_implementation()`.

Validated run:

```powershell
$env:PYTHONPATH='src'
$env:ETHERSCAN_API_KEY = 'cache-only-placeholder'
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets-sc01-historical-6.json --output runs/sc01-historical-6-v14-wormhole-source-truth --bootstrap-adapters --source-cache-dir runs/sc01-historical-6-v11-audius-runtime/_cache/etherscan-v2
```

Wormhole result:

- target id: `CT-24700f446e33`;
- queue count changed from `0` to `3`;
- `source_truth_verified_count=1`;
- evidence kind: `wormhole_uninitialized_implementation`;
- `implementation_address=0x3c3d457f1522d3540ab3325aa5f1864e34cba9d0`;
- `foundry_allowed=false`;
- missing runtime pieces:
  - `wormhole_governance_vm_payload_builder`;
  - `malicious_initializer_implementation_contract`;
  - `runtime_runner_wormhole_uninitialized_implementation`.

Decision:

- Wormhole is now source-truth verified for the historical implementation
  context, but runtime remains blocked correctly.
- Next slice is a Wormhole-specific VM/payload and malicious implementation
  harness builder.

## PT-027.T10 - Wormhole historical fork runtime runner

Status: done implementation slice, 2026-06-21.

Implemented:

- added `src/vassago_contract_runtime/sc01_wormhole.py`;
- added interface-only `VassagoSC01Harness` for Wormhole:
  - reads the historical implementation from the proxy EIP-1967 slot with
    `vm.load`;
  - initializes the implementation context with an attacker guardian;
  - builds and signs a Wormhole governance VM payload locally with `vm.sign`;
  - deploys `MaliciousImplementation` and delegates into `selfdestruct`;
  - asserts historical implementation code length becomes zero in the fork.
- `CompileOnlyAdapter` and `RuntimeFoundryAdapter` now choose the Wormhole
  harness only for the canonical Wormhole proxy target.
- `RuntimeFoundryAdapter` now uses Wormhole fork block `13_818_843`.
- `SourceTruthAdapter` now emits `runtime_runner=wormhole_implementation_runtime`
  when Wormhole source truth is complete.
- `OnChainStateAdapter` accepts the Wormhole runner as local/fork state ready.

Validation:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.design_runtime.test_sc01_source tests.design_runtime.test_phases
```

Observed:

```text
32 tests passed
```

Real smoke:

```powershell
$env:PYTHONPATH='src'
$env:ETHERSCAN_API_KEY = '<cache-only-placeholder>'
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets-sc01-historical-6.json --output runs/sc01-historical-6-v16-wormhole-runtime --bootstrap-adapters --source-cache-dir runs/sc01-historical-6-v11-audius-runtime/_cache/etherscan-v2 --runtime-authorized
python -m vassago_contract_runtime.cli impact-review --run runs/sc01-historical-6-v16-wormhole-runtime --target-id CT-24700f446e33
```

Observed Wormhole result:

- target id: `CT-24700f446e33`;
- `compile_status=compile_only_passed`;
- `runtime_status=runtime_completed`;
- `[PASS] testWormholeImplementationInitializerReplayExecutesMaliciousDelegatecall()`;
- `assertion-result.status=passed`;
- `evidence_status=runtime_local`;
- `no_broadcast=true`;
- fork block: `13_818_843`;
- impact review verdict: `historical_reproduced_critical`;
- current live risk: `not_claimed`.

Important limits:

- this is local/fork-only and uses no broadcast;
- this proves historical local/fork reachability of the malicious initializer
  delegatecall path, not current live exploitability;
- the selfdestruct path remains in the harness, but the immediate assertion is
  a storage marker written during malicious delegatecall because code deletion
  is a transaction-final effect and newer EVM semantics differ.

## PT-027.T11 - Nomad bridge root/proof runtime mapper

Status: done implementation + real runtime smoke, 2026-06-21.

Implemented:

- added `src/vassago_contract_runtime/sc01_nomad.py`;
- added corpus thesis:
  `designs/sc01-access/corpus/bridge-root-proof-validation.yaml`;
- `SourceTruthAdapter` now recognizes
  `thesis_id=bridge_root_proof_validation` and emits:
  - `evidence_kind=nomad_root_proof_message_auth_bypass`;
  - `runtime_runner=nomad_bridge_root_proof_runtime`;
  - `fork_block_number=15_259_100`;
- `CompileOnlyAdapter` and `RuntimeFoundryAdapter` now select the Nomad
  interface-only harness separately from Wormhole;
- `OnChainStateAdapter` accepts the Nomad runner as local/fork state ready;
- impact review supports Nomad as historical reproduced critical, with current
  live risk explicitly `not_claimed`.

Real smoke:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets-sc01-historical-6.json --output runs/sc01-historical-6-v18-nomad-runtime --bootstrap-adapters --source-cache-dir runs/sc01-historical-6-v11-audius-runtime/_cache/etherscan-v2 --runtime-authorized
python -m vassago_contract_runtime.cli impact-review --run runs/sc01-historical-6-v18-nomad-runtime --target-id CT-05f41610b129
```

Observed Nomad result:

- target id: `CT-05f41610b129`;
- source truth:
  - `uninitialized_implementation_proxy` rejected;
  - `bridge_root_proof_validation` verified;
- compile: `compile_only_passed`;
- runtime: `runtime_completed`;
- assertion: `passed`;
- Foundry test:
  `[PASS] testNomadProcessesUnprovenForgedMessageOnHistoricalFork()`;
- evidence status: `runtime_local`;
- impact review verdict: `historical_reproduced_critical`;
- current live risk: `not_claimed`;
- broadcast: no.

Important limits:

- the current proxy source resolves to a fixed implementation; the reproduction
  uses a pinned historical fork and does not claim current live exploitability;
- the harness proves root/proof message-authentication bypass locally by
  processing a forged unproven message into a local receiver;
- do not reuse the Wormhole VM runner for Nomad.

## PT-027.T12 - Furucombo delegatecall/proxy-storage mapper

Status: done implementation + real runtime smoke, 2026-06-22.

Implemented:

- added `src/vassago_contract_runtime/sc01_furucombo.py`;
- added corpus thesis
  `designs/sc01-access/corpus/furucombo-delegatecall-proxy-storage.yaml`;
- corrected the historical fixture to use vulnerable Furucombo proxy
  `0x17e8Ca1b4798B97602895f63206afCd1Fc90Ca5f`;
- integrated source-truth, compile-only, runtime Foundry, on-chain state gate
  and impact review.

Observed:

- run: `runs/sc01-historical-6-v22-furucombo-alchemix-runtime`;
- target id: `CT-2964504f0811`;
- compile: `compile_only_passed`;
- runtime: `runtime_completed`;
- assertion: `passed`;
- Foundry test:
  `[PASS] testFurucomboWhitelistedProxyDelegatecallDrainsVictimAllowance()`;
- impact verdict: `historical_reproduced_critical`;
- current live risk: `not_claimed`;
- broadcast: no.

## PT-027.T13 - Alchemix keeper-state mapper

Status: done implementation + real runtime smoke, 2026-06-22.

Implemented:

- added `src/vassago_contract_runtime/sc01_alchemix.py`;
- added corpus thesis `designs/sc01-access/corpus/alchemix-keeper-state.yaml`;
- integrated source-truth, compile-only, runtime Foundry, on-chain state gate
  and impact review.

Observed:

- run: `runs/sc01-historical-6-v22-furucombo-alchemix-runtime`;
- target id: `CT-4b5839bd1d37`;
- compile: `compile_only_passed`;
- runtime: `runtime_completed`;
- assertion: `passed`;
- Foundry test:
  `[PASS] testAlchemixGenericKeeperCanTriggerLowMinHarvest()`;
- impact verdict: `historical_reproduced_high_context`;
- current live risk: `not_claimed`;
- broadcast: no.

## PT-027.T14 - SC01 historical reproduction report

Status: done, 2026-06-22.

Artifact:

- `SC01_HISTORICAL_REPRODUCTION_REPORT.md`.

## PT-027.T15 - Nomad root/proof analysis + current-state separation

Status: done implementation, 2026-06-22.

Implemented:

- strengthened `src/vassago_contract_runtime/sc01_nomad.py` with
  `build_nomad_root_proof_analysis()`;
- phase 05 now emits `nomad-root-proof-analysis.json` whenever
  `bridge_root_proof_validation` is in the thesis queue;
- phase 06 now emits `bridge-state-review.json` for Nomad and no longer labels
  Nomad as local initializer state;
- `bridge-state-review.json` records:
  - root/proof model;
  - deterministic forged message plan;
  - runtime assertions;
  - current-state checks required before any live-risk claim.

Key decision:

- Nomad remains historical local/fork reproduction. Current live risk stays
  `not_claimed` unless a separate current implementation/root/message/recipient
  review is performed.

## PT-027.T16 - Nomad current-state read-only review

Status: done implementation + real read-only smoke, 2026-06-22.

Implemented:

- added `src/vassago_contract_runtime/sc01_current_state.py`;
- added CLI command:
  `python -m vassago_contract_runtime.cli current-state-review --run <run> --target-id <target>`;
- current-state review writes:
  - `12_current_state_review/sc01-current-state-review.json`;
  - `12_current_state_review/sc01-current-state-review.md`.

Nomad read-only checks:

- current implementation from Explorer proxy context;
- `eth_getCode` for proxy and implementation;
- `localDomain()`;
- `acceptableRoot(bytes32(0))`;
- `confirmAt(bytes32(0))`;
- deterministic forged message hash;
- `messages(forged_message_hash)`;
- current source check for `process(bytes)` and `acceptableRoot(...)`.

Real smoke:

- run: `runs/sc01-historical-6-v23-nomad-sidecars`;
- target id: `CT-05f41610b129`;
- current block: `25372508`;
- implementation: `0x7f221a1850c12b57fed1f0831dd25399a13b68c2`;
- `acceptableRoot(bytes32(0)) == false`;
- `confirmAt(bytes32(0)) == 1`;
- `messages(forged_message_hash) == 0x00...00`;
- source still routes `process(bytes)` through
  `acceptableRoot(messages[messageHash])`, but current `acceptableRoot` rejects
  `LEGACY_STATUS_NONE`;
- verdict: `current_default_root_path_rejected`;
- current live risk:
  `not_indicated_by_current_default_root_probe`.

Security boundary:

- read-only RPC only;
- no transaction, no signing, no broadcast;
- historical reproduction is not promoted to live exploitability.

## PT-027.T17 - Bridge current-path review sidecar

Status: done implementation + real static/read-only smoke, 2026-06-22.

Implemented:

- added `src/vassago_contract_runtime/sc01_bridge_review.py`;
- added CLI command:
  `python -m vassago_contract_runtime.cli bridge-current-review --run <run> --target-id <target>`;
- bridge current-path review writes:
  - `12_current_state_review/sc01-bridge-current-review.json`;
  - `12_current_state_review/sc01-bridge-current-review.md`.

Paths reviewed:

- `endpoint_source_validation`;
- `processed_message_replay`;
- `root_proof_verifier`;
- `escrow_supply_delta`;
- `recipient_asset_moving`.

Real smoke:

- run: `runs/sc01-historical-6-v23-nomad-sidecars`;
- target id: `CT-05f41610b129`;
- protocol fingerprint: `nomad_replica`;
- `root_proof_verifier`: `candidate_ready_for_state_review`;
- `processed_message_replay`: `blocked_reader_missing`;
- `escrow_supply_delta`: `blocked_reader_missing`;
- `recipient_asset_moving`: `blocked_asset_delta_missing`;
- current live risk: `not_claimed`.

Security boundary:

- static/source/ABI sidecar only;
- no RPC write, no transaction, no signing, no broadcast;
- no runtime Foundry execution;
- no live exploitability claim.

# PT-028 - Historical Exploit Corpus

## PT-028.T01 - Research historical exploit sources

Status: done first slice, 2026-06-22.

Sources used:

- `SunWeb3Sec/DeFiHackLabs`, cloned at commit `c496513`;
- DeFiHackLabs incident explorer;
- `SunWeb3Sec/DeFiVulnLabs`;
- `MetaTrustLabs/SmartContractAttackPoC`;
- Rekt leaderboard and SlowMist Hacked as expansion references.

Decision:

- Use historical exploit repositories as benchmark/evaluation input, not as
  detector rules.
- Keep PoC code external. The runtime corpus stores metadata, target address,
  family and scoring-only hidden labels.

## PT-028.T02 - Seed 100 balanced historical cases

Status: done, 2026-06-22.

Artifacts:

- `designs/historical-exploits/manifest.json`;
- `designs/historical-exploits/README.md`;
- `designs/historical-exploits/targets-blind-100.json`.

Current corpus:

- `100` cases total;
- `20` SC01/access-control;
- `20` bridge/message-auth;
- `20` oracle/accounting;
- `20` reentrancy/token;
- `20` proxy/upgrade/signature;
- `100` blind benchmark targets;
- `0` duplicate targets;
- `0` invalid cases;
- `96` cases with attack tx metadata;
- `90` cases with fork block metadata;
- `74` cases with explicitly annotated vulnerable contract metadata.

Safety boundary:

- `blind_inputs` is allowed for detector runs;
- `hidden_ground_truth` is scoring-only;
- no private keys, no broadcast, no live exploit claim.

## PT-028.T03 - Historical corpus CLI and tests

Status: done, 2026-06-22.

Implemented:

- `src/vassago_contract_runtime/historical_corpus.py`;
- CLI command:
  `python -m vassago_contract_runtime.cli historical-corpus-report`;
- tests:
  `tests/design_runtime/test_historical_corpus.py`.

Validation command:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli historical-corpus-report --targets-output designs/historical-exploits/targets-blind-100.json
python -m unittest tests.design_runtime.test_historical_corpus
```

Observed:

- `status=completed`;
- `case_count=100`;
- `target_count=100`;
- `duplicate_target_count=0`;
- `invalid_cases=[]`;
- focused tests passed.

## PT-028.T04 - Blind benchmark run

Status: next.

Run the design against the blind target list. The detector must not read
`hidden_ground_truth` during this phase.

Command:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets designs/historical-exploits/targets-blind-100.json --output runs/sc01-historical-blind-100-v1 --source-cache-dir runs/source-cache-v20 --bootstrap-adapters
```

Acceptance:

- per-family runtime/source/Slither failure counts are visible;
- no hidden labels are consumed by phases;
- no Foundry runtime unless the normal proof gate marks runtime-ready.

Observed blind benchmark:

- run: `runs/sc01-historical-blind-100-v1`;
- `100/100` final reports after one resume;
- first pass had one Windows manifest write failure on HEC-054/LUSD
  (`WinError 5`); resume reexecuted the target and completed cleanly;
- no broadcast and no runtime authorization in the blind run.

## PT-028.T05 - Post-run scoring

Status: done implementation + smoke, 2026-06-22.

Implemented:

- `src/vassago_contract_runtime/historical_scoring.py`;
- CLI command:
  `python -m vassago_contract_runtime.cli historical-corpus-score`;
- tests:
  `tests/design_runtime/test_historical_scoring.py`.

The scorer compares run outputs with `hidden_ground_truth` only after the blind
run:

- true positive / false negative by family;
- source failure by chain/compiler/import;
- thesis mismatch;
- runtime-ready count;
- required mapper/corpus expansion.

Current signal buckets:

- `missing`;
- `none`;
- `candidate`;
- `source_truth`;
- `compile_only`;
- `runtime_ready`;
- `runtime`.

Smoke command:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli historical-corpus-score --run runs\sc01-historical-6-v23-nomad-sidecars --manifest designs\historical-exploits\manifest.json --limit 2 --output-dir runs\_score-smoke-limit2
```

Observed:

- `status=completed`;
- artifacts written:
  - `historical-corpus-score.json`;
  - `historical-corpus-score.md`.

## PT-028.T05B - Score blind benchmark

Status: next after PT-028.T04.

Command:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli historical-corpus-score --run runs/sc01-historical-blind-100-v1 --manifest designs/historical-exploits/manifest.json --output-dir runs/sc01-historical-blind-100-v1/historical-corpus-score
```

Observed:

- `case_count=100`;
- `scored_count=100`;
- `candidate_count=67`;
- `none_count=32`;
- `runtime_ready_count=1`;
- `runtime_count=0`;
- runtime-ready case: `HEC-031` / Nomad bridge.

## PT-028.T05C - Runtime follow-up for actionable HEC-031

Status: done, 2026-06-22.

Command:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets runs/_selected/hec-031-target.json --output runs/sc01-historical-blind-hec031-runtime-v1 --source-cache-dir runs/source-cache-historical-100 --bootstrap-adapters --runtime-authorized
python -m vassago_contract_runtime.cli historical-corpus-score --run runs/sc01-historical-blind-hec031-runtime-v1 --manifest designs/historical-exploits/manifest.json --benchmark-id HEC-031 --output-dir runs/sc01-historical-blind-hec031-runtime-v1/historical-corpus-score-hec031
```

Observed:

- target: `HEC-031`, Nomad Replica;
- runtime: `runtime_completed`;
- evidence: `runtime_local`;
- Foundry command was local/fork only with redacted RPC URL;
- assertion passed:
  `testNomadProcessesUnprovenForgedMessageOnHistoricalFork`;
- score with `--benchmark-id HEC-031`:
  `case_count=1`, `runtime_count=1`.

Boundary:

- This is historical fork-local reproduction.
- It is not a current live exploitability claim.

## PT-028.T07 - Blind score triage

Status: next.

Input:

- `runs/sc01-historical-blind-100-v1/historical-corpus-score/historical-corpus-score.json`.

Tasks:

- inspect the `67` candidate-only cases by family;
- inspect the `32` none cases by family;
- separate source-resolution/compiler/import misses from real detector misses;
- create mapper tasks for the highest-value misses;
- keep HEC-031 as known runtime proof, not as a rule.

## PT-028.T06 - Corpus expansion to 100+

Status: queued.

Expand beyond the first 100 with stricter curation:

- normalize chain for every target;
- verify target roles against PoC comments/source;
- import additional historical cases from licensed/local sources;
- keep external PoC code out of runtime artifacts unless license is reviewed.
