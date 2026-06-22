# Context

## Mission

Build a clean campaign runtime for Vassago that can run security designs against
deployed smart contracts in a repeatable, resumable and evidence-safe way.

The immediate use case is SC01 Access Control, but the runtime must be generic
enough to later host SC02-SC10 designs.

## Primary Domain Terms

### ContractTarget

The unit of work:

```text
(chain, address)
```

A target can be enriched with ABI, source, proxy context, bytecode, storage,
logs, balances, tx history, compile context and local proof artifacts.

### Design

A versioned campaign definition. Example: `sc01-access`.

A Design contains phases, required inputs, artifacts, gates and final report
rules.

### Phase

A deterministic step in a Design. A Phase has:

- id;
- name;
- inputs;
- outputs;
- gate behavior;
- resume behavior;
- status.

### Run

One execution of a Design over one or more ContractTargets.

Every Run must have a `run-manifest.json`.

### Artifact

Structured output written by a Phase. Artifacts are indexed by run, target and
phase.

### Thesis

A concrete vulnerability hypothesis. For SC01 examples:

- uninitialized implementation/proxy;
- weak UUPS authorization;
- Safe module/fallback abuse;
- bridge endpoint/source validation;
- role admin/self-admin escalation;
- hook/callback caller validation;
- arbitrary sender/from.

### ProofPiece

Required proof element before runtime:

- source-truth guard gap;
- actor model;
- codable args;
- measurable reader;
- measurable delta;
- explicit predicate;
- compile-only pass.

### RuntimeProof

Local/fork deterministic execution proving or rejecting the thesis.

## Non-Goals

- No chain broadcast.
- No generic shell MCP.
- No evidence promotion from LLM output.
- No static finding promoted to reproduced issue.
- No random large batch before campaign metrics exist.

## Relationship To Original Vassago

The old Vassago repo contains many working adapters and tools. This repo should
not copy the entire tool surface. It should import or reimplement only behind
deep Interfaces:

- SourceResolver Adapter. Interface done; null, local fixture and
  Explorer-backed resolver done.
- Explorer Adapter. Interface plus Etherscan V2 read-only cache adapter done.
- Slither Adapter. Interface plus null and subprocess adapter done.
- Foundry Adapter. Interface plus null adapter done.
- ArtifactStore Adapter;
- Corpus Adapter. Interface and local design corpus adapter done.

## Current Runtime State

As of 2026-06-21:

- phase 00 intake is a real local adapter;
- phase 01 dossier is a real local skeleton adapter;
- phase 01 can consume ABI/source through `--source-fixture`;
- phase 01 can consume real read-only Explorer source context through
  Etherscan V2 when no `--source-fixture` is supplied;
- phase 02 semantic surface is a real local skeleton adapter;
- phase 02 now prefers normalized Slither IR when compile context and a
  Slither adapter/payload are available, then falls back to ABI/source
  heuristic with explicit `extraction_source`;
- phase 03 corpus motifs is a real local skeleton adapter;
- phase 04 thesis acquisition is a real local skeleton adapter;
- phase 05 source truth is a real local skeleton adapter;
- phase 06 on-chain state is a real local skeleton adapter;
- phase 07 proof pieces is a real local skeleton adapter;
- phase 08 compile-only is a real local skeleton adapter;
- phase 09 runtime Foundry has a local-only gated adapter;
- phase 10 final report is a real local skeleton adapter;
- Etherscan V2 provider is now called by phase 01 in bootstrap mode when no
  `--source-fixture` is supplied; missing `ETHERSCAN_API_KEY` returns a
  structured unresolved source state;
- Slither subprocess adapter exists but is not called by bootstrap mode;
- Slither CLI JSON is treated as detector context only; full function
  writes/modifiers/calls require normalized IR or the Python API path;
- Slither Python API adapter is wired in bootstrap mode and fills normalized IR
  when `slither-analyzer` plus compatible local solc are available;
- Foundry interface exists with null and subprocess adapters;
- `SubprocessFoundryAdapter.compile_harness()` can run local `forge build`;
- `SubprocessFoundryAdapter.run_local_fork()` is gated by explicit
  `runtime_ready=true` and `runtime_authorized=true`;
- positive local fixture `tests/fixtures/source_fixture_positive.json` reaches
  `runtime_ready_count=1`, compiles with `forge build`, and runs local
  `forge test` only when `--runtime-authorized` is passed;
- source-backed verifier `src/vassago_contract_runtime/sc01_source.py` now
  drives that positive path; it no longer depends on
  `metadata.local_positive_sc01_case`;
- the same module contains source-backed negative policy for public normal
  behavior; `initializeMarket()` in the negative fixture is rejected as
  `caller_funded_accounting` and cannot reach Foundry;
- `runtime_api.py` is the shared CLI/tool entrypoint for run/resume/artifact
  read;
- `tools/` exposes three campaign-level contracts:
  `vassago_design_run`, `vassago_design_resume` and `vassago_artifact_read`;
- `mcp/` exposes a local stdio MCP server over those three contracts;
- CLI command `python -m vassago_contract_runtime.cli mcp --stdio` is
  available;
- Hermes MCP server `vassago_contract_runtime` is configured locally and points
  to `scripts/hermes-vassago-contract-runtime-mcp.cmd`;
- Hermes skill `vassago-sc01-design` is installed locally and versioned under
  `designs/sc01-access/prompts/vassago-sc01-design.md`;
- no RPC or broadcast path is wired.
- no RPC or broadcast path is wired.

## Explorer-backed source resolution

`PT-025.T01B` wires real read-only source resolution into phase 01:

- `src/vassago_contract_runtime/contracts/source_resolver.py` defines
  `ExplorerSourceResolver`.
- `src/vassago_contract_runtime/runtime_api.py` chooses
  `FixtureSourceResolver` when `--source-fixture` is supplied.
- Without `--source-fixture`, bootstrap mode uses
  `ExplorerSourceResolver(EtherscanV2ExplorerAdapter(...))`.
- Default cache path is `<output>/_cache/etherscan-v2` for `run-design` and
  `<run>/_cache/etherscan-v2` for `resume`.
- CLI/tool payloads can override the cache path through `source_cache_dir` /
  `--source-cache-dir`.

Safety:

- Explorer source resolution is read-only.
- It uses `ETHERSCAN_API_KEY` from the environment.
- If the key is absent, artifacts record `etherscan_api_key_missing`; no fake
  source is generated.
- Cache keys exclude the API key.

## Slither IR Extraction State

`PT-024.T15` is implemented in conservative form:

- `01_dossier/compile-context.json` is `available` when source files exist;
- `02_semantic_surface/access-surface.json` records a `slither` summary;
- functions extracted from normalized IR are marked
  `extraction_source=slither_ir` and `confidence=high`;
- when no Slither adapter or IR payload exists, the phase falls back to
  `abi_source_heuristic` / `abi_only`.

`PT-024.T16` adds real Slither Python API extraction:

- `PythonSlitherAdapter` imports `slither.slither.Slither` optionally;
- source bundles are written to an ephemeral workspace;
- the adapter runs from that workspace to avoid Windows absolute-path issues;
- normalized IR includes modifiers, state reads/writes, variables read/written,
  internal/external calls, conditions, SlithIR operation strings and source
  mapping;
- `runtime_api.py` wires it by default in bootstrap mode.

Current limit:

Slither real runs use controlled compiler cache/provisioning:

- `PT-024.T17` selects installed compiler versions by setting `SOLC_VERSION`
  from `compile-context.json`.
- `PT-024.T18` adds `SolcSelectManager`, which lists the local solc-select
  cache and can install missing versions only when `allow_solc_install=true`.
- The runtime never calls `solc-select use`, so global compiler state is not
  changed.
- `access-surface.json.slither.compiler_selection.provisioning` records
  installed versions, cache status, install attempt, manager and errors.
- With default settings, missing compilers produce structured
  `solc_version_cache_missing` and phase 02 falls back to heuristic extraction.

## Current Positive Fixture

The local positive SC01 fixture models the historical UUPS uninitialized
implementation pattern:

```text
tests/fixtures/targets_positive.json
tests/fixtures/source_fixture_positive.json
```

Command:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets_positive.json --output runs/sc01-positive-local-runtime --source-fixture tests/fixtures/source_fixture_positive.json --bootstrap-adapters --runtime-authorized
```

Expected current result:

```text
source_truth_verified_count=1
runtime_ready_count=1
compile_status=compile_only_passed
runtime_status=runtime_completed
evidence_status=runtime_local
no_broadcast=true
```

Negative anti-hardcode fixture:

```text
tests/fixtures/targets_negative.json
tests/fixtures/source_fixture_negative.json
```

This fixture intentionally contains `initializeMarket()` so the corpus emits an
initializer-like candidate. Source truth rejects it as caller-funded accounting:

```text
source_truth_rejected_count=1
runtime_ready_count=0
foundry_allowed=false
```

Limit:

This is a local regression fixture, not a live-contract claim. The source-backed
verifier proves initializer/write/reader/sink conditions from local source, but
real contracts still need proxy/state impact before runtime.

## Current Real Curated Smoke

`PT-027.T03` current curated real baseline is:

```text
runs/sc01-curated-real-20-v8
```

Current result:

- 20 curated ETH/BSC/Base targets;
- all 20 source bundles resolved through Etherscan V2;
- all 20 compile contexts selected usable target source;
- all 20 Slither Python runs completed;
- 13 SC01 thesis candidates reached source-truth review;
- all 13 were source-truth rejected by negative policy;
- all 20 final reports are `blocked_no_runtime_ready`;
- all 20 have `foundry_allowed=false`;
- `runtime_ready_total=0`.

Rejection classes:

- transparent proxy admin path;
- initialized EIP-1967 proxy with known implementation context;
- protocol pool initializer;
- public factory/pool creation;
- token approval/operator APIs;
- caller-funded accounting/lifecycle/operator behavior.

This means the read-only Explorer/source/Slither path works for the curated
sample and broad false candidates are terminalized before Foundry. It does not
mean SC01 found a vulnerability. Runtime Foundry remains blocked until a fresh
report has complete proof pieces and
`foundry_allowed=true`.

## Current Adversarial Fixture Slice

`PT-027.T01` first slice adds local adversarial SC01 coverage:

```text
tests/fixtures/targets_adversarial.json
tests/fixtures/source_fixture_adversarial.json
designs/sc01-access/corpus/tx-origin-auth.yaml
designs/sc01-access/corpus/role-admin-escalation.yaml
designs/sc01-access/corpus/public-lifecycle-noise.yaml
```

Covered behavior:

- `FixtureDisabledInitializer` has `initialize()` and `upgradeTo(...)`, but
  constructor calls `_disableInitializers()`. It must not become source-truth
  verified.
- `FixtureTxOriginAdmin` uses `tx.origin == owner`. It must route as
  `tx_origin_authorization` but must not reach Foundry without complete proof
  pieces.
- `FixtureOpenRoleAdmin` has public `grantOperator(address)`. It must route as
  `role_admin_escalation` but remains blocked until role reader/delta and actor
  model are complete.
- `FixturePublicLifecycle` has public `settleRound()` and timestamp-gated
  lifecycle writes. It must be rejected as `public_lifecycle`.

Primary regression:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.design_runtime.test_phases -v
```

This is anti-hardcode coverage. It is not live-chain evidence and does not prove
severity.

## Current Historical SC01 Runtime Evidence

`PT-027.T05` adds a small historical curated suite:

```text
tests/fixtures/targets-sc01-historical-6.json
runs/sc01-historical-6-v4-runtime
```

The suite contains BadgerDAO, Audius, Nomad, Furucombo, Alchemix and Wormhole
targets. The current result is:

```text
source_resolved=6/6
slither_completed=5/6
source_truth_verified_total=1
runtime_ready_total=1
foundry_allowed=1
compile_passed=1
runtime_completed=1
```

The one reproduced local runtime case is BadgerDAO `WarRoomGatedProxy`:

```text
predicate=After an unauthorized caller invokes initialize(), hasRole(DEFAULT_ADMIN_ROLE, caller) is true.
measured_delta=hasRole(DEFAULT_ADMIN_ROLE, unauthorized caller) changes false to true
evidence_status=runtime_local
no_broadcast=true
```

This is local Foundry reproduction of an uninitialized AccessControl initializer
pattern. It is not a live funds-at-risk claim. Live impact still requires
separate state/proxy/asset analysis for any target.

Remaining historical blockers:

- Audius: governance/proxy implementation-state mapper.
- Nomad: bridge root/proof mapper plus Slither failure triage.
- Furucombo: delegatecall/proxy-storage mapper.
- Alchemix: keeper actor/state-delta mapper.
- Wormhole: implementation initializer/UUPS context mapper.

## Current Audius Proxy-Collision Runtime Evidence

`PT-027.T07` current Audius baseline is:

```text
runs/sc01-historical-6-v11-audius-runtime
```

The run was executed with `ETHERSCAN_API_KEY` and `VASSAGO_FORK_RPC_*` loaded
from `C:\Users\PC\Desktop\Vassago\.env` into the process without printing
values.

Current Audius status:

- proxy source resolved through Etherscan V2;
- proxy context reports implementation
  `0x1c91af03a390b4c619b444425b3119e553b5b44b`;
- related implementation source resolved as contract `Governance`;
- `upgradeTo(address)` is rejected as `custom_proxy_admin_path`, not weak UUPS;
- new thesis `proxy_storage_collision_reinitializer` reaches source truth;
- source truth status:
  `source_truth_verified`;
- implementation Initializable flags and `initialize(...)` are detected;
- initializer privileged writes are detected with readers:
  - `registry` / `getRegistryAddress()`;
  - `votingPeriod` / `getVotingPeriod()`;
  - `executionDelay` / `getExecutionDelay()`;
  - `maxInProgressProposals` / `getMaxInProgressProposals()`;
  - `votingQuorumPercent` / `getVotingQuorumPercent()`;
  - `guardianAddress` / `getGuardianAddress()`;
- delegated initializer plan:
  `initialize(address,uint256,uint256,uint256,uint16,address)` with
  `address(this), 3, 0, 1, 4, address(this)`;
- fork block: `15201793`;
- `foundry_allowed=true`;
- `compile_status=compile_only_passed`;
- `runtime_status=runtime_completed`;
- `assertion-result.status=passed`;
- evidence status: `runtime_local`;
- broadcast: no.

This is historical fork/local reproduction of the Audius initializer replay
proxy-collision thesis. It is not a current live funds-at-risk claim.

## Current Impact Review State

Audius now has a conservative sidecar impact review:

```text
runs/sc01-historical-6-v11-audius-runtime/targets/CT-3f08e02c1bef/phases/11_impact_review/sc01-impact-review.json
```

Current Audius impact posture:

- historical reproduced critical: yes;
- local/fork runtime assertion: passed;
- current live severity claim: no;
- broadcast: no.

Use:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli impact-review --run runs/sc01-historical-6-v11-audius-runtime --target-id CT-3f08e02c1bef
```

## Current Wormhole Blocker State

Wormhole is no longer blocked at acquisition. The runtime now indexes related
implementation ABI/source for proxies and has a dedicated historical fork
runner.

Baseline:

```text
runs/sc01-historical-6-v14-wormhole-source-truth
```

Current Wormhole status:

- target id: `CT-24700f446e33`;
- queue count: `3`;
- source-truth verified count: `1`;
- evidence kind: `wormhole_uninitialized_implementation`.

Runner implementation:

- module: `src/vassago_contract_runtime/sc01_wormhole.py`;
- runtime runner: `wormhole_implementation_runtime`;
- fork block: `13_818_843`;
- harness: interface-only, reads EIP-1967 implementation slot with `vm.load`,
  signs governance VM with local `vm.sign`, and asserts implementation code
  destruction in the local fork;
- no broadcast and no private key outside the local Foundry test key.

Current Wormhole runtime evidence:

- run: `runs/sc01-historical-6-v16-wormhole-runtime`;
- target id: `CT-24700f446e33`;
- compile: `compile_only_passed`;
- runtime: `runtime_completed`;
- assertion: `passed`;
- Foundry test:
  `testWormholeImplementationInitializerReplayExecutesMaliciousDelegatecall`;
- impact review:
  `runs/sc01-historical-6-v16-wormhole-runtime/targets/CT-24700f446e33/phases/11_impact_review/sc01-impact-review.json`;
- impact verdict: `historical_reproduced_critical`;
- current live risk: `not_claimed`.

Interpretation:

- Wormhole is historically reproduced in a local fork, no broadcast.
- Do not claim current live exploitability without a fresh current-state review.
- Next historical blocker is Nomad root/proof bridge mapping, which is a
  separate bridge-specific mapper and should not reuse the Wormhole VM runner.

## Current Nomad Root/Proof State

Nomad now has a separate bridge root/proof mapper and runtime harness.

Runner implementation:

- module: `src/vassago_contract_runtime/sc01_nomad.py`;
- corpus: `designs/sc01-access/corpus/bridge-root-proof-validation.yaml`;
- runtime runner: `nomad_bridge_root_proof_runtime`;
- fork block: `15_259_100`;
- harness: interface-only, crafts a local forged Nomad message, checks
  `messages(messageHash)` default state, checks `acceptableRoot(defaultRoot)`,
  calls `process(bytes)`, then asserts:
  - local receiver `handle(...)` was called;
  - `messages(messageHash)` became `LEGACY_STATUS_PROCESSED()`.

Current Nomad runtime evidence:

- run: `runs/sc01-historical-6-v18-nomad-runtime`;
- target id: `CT-05f41610b129`;
- source truth:
  - `uninitialized_implementation_proxy` rejected;
  - `bridge_root_proof_validation` verified;
- compile: `compile_only_passed`;
- runtime: `runtime_completed`;
- assertion: `passed`;
- Foundry test:
  `testNomadProcessesUnprovenForgedMessageOnHistoricalFork`;
- impact review:
  `runs/sc01-historical-6-v18-nomad-runtime/targets/CT-05f41610b129/phases/11_impact_review/sc01-impact-review.json`;
- impact verdict: `historical_reproduced_critical`;
- current live risk: `not_claimed`.

Interpretation:

- Nomad is historically reproduced in a local fork, no broadcast.
- The current proxy source resolves to a fixed implementation. Do not claim
  current live exploitability without a fresh current-state review.
- The Nomad mapper is bridge root/proof-specific and must remain separate from
  Wormhole's implementation-initializer VM runner.
- PT-027.T15 strengthens this with two explicit sidecars:
  - phase 05 `nomad-root-proof-analysis.json`;
  - phase 06 `bridge-state-review.json`.
- These sidecars record the root/proof model, deterministic forged message
  plan, runtime assertions and current-state checks required before any
  live-risk claim.

## Current Nomad Current-State Review

Nomad now has a read-only current-state review command:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli current-state-review --run runs/sc01-historical-6-v23-nomad-sidecars --target-id CT-05f41610b129
```

Current artifact:

```text
runs/sc01-historical-6-v23-nomad-sidecars/targets/CT-05f41610b129/phases/12_current_state_review/sc01-current-state-review.json
```

Observed on 2026-06-22:

- block: `25372508`;
- implementation from Explorer proxy context:
  `0x7f221a1850c12b57fed1f0831dd25399a13b68c2`;
- `acceptableRoot(bytes32(0)) == false`;
- `confirmAt(bytes32(0)) == 1`;
- `messages(forged_message_hash) == 0x00...00`;
- current source still calls `acceptableRoot(messages[messageHash])`, but
  `acceptableRoot` rejects `LEGACY_STATUS_NONE`;
- verdict: `current_default_root_path_rejected`;
- current live risk:
  `not_indicated_by_current_default_root_probe`.

Interpretation:

- The historical Nomad default-root exploit path is rejected by current
  default-root handling.
- This does not prove every bridge path safe; it specifically rejects the
  reproduced historical default-root path in current state.

## Current Bridge Current-Path Review

Bridge live-risk follow-up now has a static/read-only router command:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli bridge-current-review --run runs/sc01-historical-6-v23-nomad-sidecars --target-id CT-05f41610b129
```

Current artifact:

```text
runs/sc01-historical-6-v23-nomad-sidecars/targets/CT-05f41610b129/phases/12_current_state_review/sc01-bridge-current-review.json
```

Observed on 2026-06-22:

- protocol fingerprint: `nomad_replica`;
- `endpoint_source_validation`: `not_detected`;
- `processed_message_replay`: `blocked_reader_missing`;
- `root_proof_verifier`: `candidate_ready_for_state_review`;
- `escrow_supply_delta`: `blocked_reader_missing`;
- `recipient_asset_moving`: `blocked_asset_delta_missing`;
- current live risk: `not_claimed`.

Interpretation:

- Do not keep insisting on the Nomad default-root path after the read-only
  current-state rejection.
- For bridge live risk, use this sidecar to choose a concrete current path:
  endpoint/source validation, processed-message replay, root/proof verifier,
  escrow/supply delta or recipient asset-moving.
- This sidecar is static/source/ABI triage. It does not use RPC writes, does
  not execute Foundry and does not claim live exploitability.

## Current SC01 Historical Reproduction Inventory

Consolidated report:

```text
SC01_HISTORICAL_REPRODUCTION_REPORT.md
```

Historical local/fork cases currently reproduced:

- Audius governance proxy:
  `runs/sc01-historical-6-v11-audius-runtime`,
  `CT-3f08e02c1bef`, `historical_reproduced_critical`;
- Wormhole core bridge:
  `runs/sc01-historical-6-v16-wormhole-runtime`,
  `CT-24700f446e33`, `historical_reproduced_critical`;
- Nomad Replica:
  `runs/sc01-historical-6-v18-nomad-runtime`,
  `CT-05f41610b129`, `historical_reproduced_critical`;
- Furucombo proxy v1.0.0:
  `runs/sc01-historical-6-v22-furucombo-alchemix-runtime`,
  `CT-2964504f0811`, `historical_reproduced_critical`;
- Alchemix Harvester:
  `runs/sc01-historical-6-v22-furucombo-alchemix-runtime`,
  `CT-4b5839bd1d37`, `historical_reproduced_high_context`.

All five are local/fork-only, no broadcast, and current live risk remains
`not_claimed` unless a fresh current-state review proves otherwise.

## Current Historical Exploit Corpus

PT-028 adds the first benchmark-grade historical exploit corpus seed.

Artifacts:

```text
designs/historical-exploits/manifest.json
designs/historical-exploits/README.md
designs/historical-exploits/targets-blind-100.json
```

Source:

- `SunWeb3Sec/DeFiHackLabs`, local clone
  `C:\Users\PC\AppData\Local\Temp\vassago-research\DeFiHackLabs`, commit
  `c496513`;
- the corpus stores metadata only. It does not copy PoC Solidity into runtime
  fixtures.

Current counts:

- `100` cases total;
- `20` `sc01_access_control`;
- `20` `bridge_message_auth`;
- `20` `oracle_accounting`;
- `20` `reentrancy_token`;
- `20` `proxy_upgrade_signature`;
- `100` blind benchmark targets;
- `0` duplicate targets;
- `0` invalid cases.

Policy:

- phases may consume only `blind_inputs`;
- `hidden_ground_truth` is post-run scoring-only;
- no private key, no write RPC, no broadcast;
- do not convert historical labels or addresses into detector hardcode.

Command to refresh the report/export:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli historical-corpus-report --targets-output designs/historical-exploits/targets-blind-100.json
```

Next execution:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets designs/historical-exploits/targets-blind-100.json --output runs/sc01-historical-blind-100-v1 --source-cache-dir runs/source-cache-v20 --bootstrap-adapters
```

Post-run scoring:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli historical-corpus-score --run runs/sc01-historical-blind-100-v1 --manifest designs/historical-exploits/manifest.json --output-dir runs/sc01-historical-blind-100-v1/historical-corpus-score
```

Current blind benchmark result:

```text
run=runs/sc01-historical-blind-100-v1
status=completed
scored_count=100
candidate_count=67
none_count=32
runtime_ready_count=1
runtime_count=0
```

The runtime-ready case was:

```text
benchmark_id=HEC-031
case_id=nomadbridge
family=bridge_message_auth
target=ethereum:0x5d94309e5a0090b165fa4181519701637b6daeba
```

Runtime follow-up:

```text
run=runs/sc01-historical-blind-hec031-runtime-v1
final_status=runtime_completed
evidence_status=runtime_local
test=testNomadProcessesUnprovenForgedMessageOnHistoricalFork
```

This is historical fork-local reproduction only. It does not claim current live
exploitability.

Scoring buckets:

- `missing`;
- `none`;
- `candidate`;
- `source_truth`;
- `compile_only`;
- `runtime_ready`;
- `runtime`.

Interpretation:

- This is the right path to measure detection quality before another random
  scan.
- It is not proof that Vassago catches those cases yet; it is the blind
  benchmark input for proving or falsifying that.

## Current stage-failure report

Generated with:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli historical-stage-report --run runs/sc01-historical-blind-100-v1 --manifest designs/historical-exploits/manifest.json --output-dir runs/sc01-historical-blind-100-v1/historical-stage-failure
```

Artifacts:

- `runs/sc01-historical-blind-100-v1/historical-stage-failure/historical-stage-failure-report.json`
- `runs/sc01-historical-blind-100-v1/historical-stage-failure/historical-stage-failure-report.md`

Observed:

```text
case_count=100
candidate_count=67
runtime_ready_count=1
runtime_count=0
04_no_thesis_candidate=32
05_source_truth_not_verified=67
09_runtime_authorization_pending=1
```

Candidate priority:

```text
proxy_upgrade_signature=17
oracle_accounting=15
reentrancy_token=14
sc01_access_control=11
bridge_message_auth=10
```

Operational meaning:

- The primary current blocker is source-truth, not Foundry.
- The next implementation should start with `proxy_upgrade_signature` because
  it has the largest candidate bucket.
- Do not turn historical labels, case ids or addresses into detector rules.
  The historical report is post-run scoring and triage only.

## PT-028.T08 Proxy/Upgrade Mapper State

`PT-028.T08` adds the first source-truth mapper for the largest blind-100
candidate bucket, `proxy_upgrade_signature`.

Files:

- `src/vassago_contract_runtime/sc01_proxy_upgrade.py`
- `src/vassago_contract_runtime/phases/source_truth.py`
- `tests/design_runtime/test_sc01_proxy_upgrade.py`

What it does:

- classifies transparent proxy admin paths as terminal for generic
  `uups_weak_auth`;
- rejects implementations with `_disableInitializers()`;
- blocks proxy candidates when implementation source is missing;
- blocks role-admin escalation when role graph/state readers are not available;
- emits source-truth verified/runtime-blocked for initializer/UUPS candidates
  only when source evidence exists, while keeping runtime blocked until proxy
  impact, upgrade target, reader/delta and codable args are known.

Observed validation:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.design_runtime.test_sc01_proxy_upgrade tests.design_runtime.test_sc01_source
```

Result:

```text
Ran 32 tests
OK
```

The mapper was also applied directly to resolved artifacts from
`runs/sc01-historical-blind-100-v1` for the 20 proxy-upgrade cases. It produced
precise classes such as:

- `transparent_proxy_admin_path`
- `disable_initializers_present`
- `proxy_implementation_source_missing`
- `role_admin_graph_required`
- `initializer_without_measurable_critical_write`
- `uninitialized_proxy_or_implementation_initializer`

Fresh isolated rerun note:

- `runs/sc01-historical-proxy-upgrade-t08-v1` completed all phases with
  `failed_count=0`, but produced `04_no_thesis_candidate=20` because the fresh
  family-only run did not route those targets into proxy-upgrade theses.
- Therefore the next blocker is `PT-028.T09` thesis acquisition/routing for
  proxy family, not Foundry.
