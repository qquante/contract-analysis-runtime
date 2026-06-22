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
