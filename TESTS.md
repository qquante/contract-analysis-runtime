# Tests

## Test Policy

Every implementation task must add or update tests before being marked done.

Status labels:

- `not_started`
- `fixture_only`
- `static_only`
- `read_only_real`
- `compile_only`
- `runtime_local`

## Initial Test Matrix

| Area | Command | Expected |
| --- | --- | --- |
| Unit | `python -m unittest discover -s tests` | all pass; current: 53 |
| Check | `python -m vassago_contract_runtime.cli check` | passes; validates SC01 design and safety checks |
| Design dry run | `python -m vassago_contract_runtime.cli run-design --dry-run ...` | passes; manifests + dry-run artifacts |
| Resume | `python -m vassago_contract_runtime.cli resume --run ... --dry-run` | passes; skips completed phases |
| SC01 fixture | run SC01 on local source fixture | no broadcast, dossier has ABI/source, corpus writes candidate-only |
| Compile-only | run compile phase on fixture | harness compiles |
| Runtime local | run Foundry local fixture only | reproduced/not_reproduced |

## Required Regression Gates

Before any commit with code:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests
python -m vassago_contract_runtime.cli check
git diff --check
```

## Latest Validation

Date: 2026-06-21.

Command:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests
```

Result:

```text
Ran 53 tests
OK
```

Coverage added:

- model validation and JSON roundtrip;
- invalid address;
- invalid phase id;
- run/target/phase manifests;
- artifact URI and hash;
- path traversal fail-closed;
- runner all phases;
- runner resume skip;
- required failure stop;
- optional failure continuation.
- simple YAML design loader;
- CLI `check`;
- CLI `run-design --dry-run`;
- CLI `resume --dry-run`;
- CLI `artifact-read`.
- SourceResolver interface and NullSourceResolver;
- phase 00 intake real local adapter;
- phase 01 dossier skeleton adapter;
- CLI `run-design --bootstrap-adapters`.
- FixtureSourceResolver local ABI/source fixture.
- ExplorerAdapter interface and NullExplorerAdapter.
- CorpusAdapter interface and DesignCorpusAdapter.
- phase 03 corpus motifs skeleton.
- CLI `run-design --bootstrap-adapters --source-fixture`.
- phase 02 semantic surface skeleton.
- phase 04 thesis acquisition skeleton.
- Etherscan V2 Explorer read-only adapter with fake transport/cache test.
- Explorer-backed SourceResolver mapping test.
- Runtime no-fixture wiring test: bootstrap mode uses Explorer resolver and
  source cache path.
- Slither adapter interface and NullSlitherAdapter.
- phase 05 source truth skeleton.
- phase 06 on-chain state skeleton.
- Foundry adapter interface and NullFoundryAdapter.
- SubprocessSlitherAdapter with fake-runner JSON parsing.
- phase 07 proof pieces skeleton.
- phase 08 compile-only skeleton.
- phase 10 final report skeleton.
- SubprocessFoundryAdapter compile and runtime gate tests with fake runner.
- Runtime tool contracts for `vassago_design_run`,
  `vassago_design_resume` and `vassago_artifact_read`.
- Tool registry alias resolution and unknown-tool fail-closed behavior.
- MCP stdio server initialize, tools/list, tools/call and notification tests.
- CLI stdio smoke for initialize + tools/list.
- Hermes MCP registration smoke with `hermes mcp test vassago_contract_runtime`.
- Hermes skill visibility smoke with `hermes skills list`.
- Positive SC01 fixture reaches `runtime_ready_count=1`.
- Source-backed UUPS initializer verifier tests cover positive source,
  `_disableInitializers()` blocker and missing reader blocker.
- Source-backed negative policy tests cover public caller-funded accounting and
  ensure admin writes are not rejected as normal behavior.
- Negative fixture `initializeMarket()` is rejected as
  `caller_funded_accounting` and does not reach Foundry.
- Local Foundry compile-only smoke passed with `forge build`.
- Local Foundry runtime smoke passed with `forge test`, one test passed, no broadcast.

Smoke:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets.json --source-fixture tests/fixtures/source_fixture.json --output <temp> --bootstrap-adapters
```

Result:

```text
RunStatus=completed
FailedCount=0
SourceStatus=resolved
FunctionCount=2
SurfaceStatus=completed
CandidateCount=2
QueueCount=2
SourceTruthStatus=blocked
SourceTruthVerifiedCount=0
AdminStateStatus=needs_provider
RuntimeReadyCount=0
FoundryAllowed=false
CompileStatus=compile_skipped_not_ready
FoundryCalled=false
FinalStatus=blocked_no_runtime_ready
ThesisIds=uninitialized_implementation_proxy,uups_weak_auth
```

MCP stdio smoke:

```powershell
$env:PYTHONPATH='src'
$inputJson = @(
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"smoke"}}}',
  '{"jsonrpc":"2.0","method":"notifications/initialized"}',
  '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'
) -join "`n"
$inputJson | python -m vassago_contract_runtime.cli mcp --stdio
```

Result:

```text
initialize returned tools capability.
tools/list returned vassago_design_run, vassago_design_resume and vassago_artifact_read.
stdout contained only JSON-RPC responses.
```

Hermes integration smoke:

```powershell
hermes mcp test vassago_contract_runtime
hermes skills list
```

Result:

```text
vassago_contract_runtime connected in stdio mode and discovered 3 tools.
vassago-sc01-design is enabled as a local domain skill.
```

Positive local runtime smoke:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets_positive.json --output runs/sc01-positive-local-runtime --source-fixture tests/fixtures/source_fixture_positive.json --bootstrap-adapters --runtime-authorized
```

Result:

```text
RunStatus=completed
FailedCount=0
SourceTruthVerifiedCount=1
RuntimeReadyCount=1
FoundryAllowed=true
CompileStatus=compile_only_passed
RuntimeStatus=runtime_completed
AssertionStatus=passed
EvidenceStatus=runtime_local
NoBroadcast=true
ForgeCommand=forge test --match-contract VassagoSC01Harness
VerificationBasis=source-backed initializer/write/reader/sink checks; no metadata shortcut
```

Negative anti-hardcode smoke:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets_negative.json --output runs/sc01-negative-t14 --source-fixture tests/fixtures/source_fixture_negative.json --bootstrap-adapters --runtime-authorized
```

Result:

```text
CandidateFunction=initializeMarket
SourceTruthStatus=source_truth_rejected
Classification=caller_funded_accounting
RuntimeReadyCount=0
FoundryAllowed=false
```

Slither IR semantic surface regression:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.design_runtime.test_phases tests.design_runtime.test_provider_adapters
```

Result:

```text
18 tests passed.
SemanticSurfaceAdapter with fake Slither IR:
- compile-context.json status=available;
- access-surface.json slither.status=completed;
- initialize() extraction_source=slither_ir;
- initialize() state_write_signals includes owner;
- initialize() guard_signals includes owner_check.
```

Full validation after PT-024.T15:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests
python -m vassago_contract_runtime.cli check
git diff --check
```

Result:

```text
54 tests passed.
check passed: 5/5 checks.
git diff --check passed with normal CRLF warnings.
```

CLI smoke after PT-024.T15:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets_positive.json --output runs/sc01-positive-t15 --source-fixture tests/fixtures/source_fixture_positive.json --bootstrap-adapters --runtime-authorized
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets_negative.json --output runs/sc01-negative-t15 --source-fixture tests/fixtures/source_fixture_negative.json --bootstrap-adapters --runtime-authorized
```

Result:

```text
Positive: runtime_completed, forge test 1 passed, no broadcast.
Negative: source_truth_rejected, foundry_allowed=false.
```

Real Slither Python API smoke after PT-024.T16:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets_positive.json --output runs/sc01-positive-t16-real-slither-3 --source-fixture tests/fixtures/source_fixture_positive.json --bootstrap-adapters --runtime-authorized
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets_negative.json --output runs/sc01-negative-t16-real-slither-2 --source-fixture tests/fixtures/source_fixture_negative.json --bootstrap-adapters --runtime-authorized
```

Result:

```text
Positive:
- slither.status=completed
- slither.provider=slither_python
- slither.ir_status=completed
- initialize().extraction_source=slither_ir
- initialize().state_write_signals=["owner"]
- final_status=runtime_completed

Negative:
- slither.status=completed
- initializeMarket().extraction_source=slither_ir
- state_write_signals=["balances", "totalDeposits"]
- source_truth_rejected
- foundry_allowed=false
```

Slither compiler selection smoke after PT-024.T17:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets_positive.json --output runs/sc01-positive-t17 --source-fixture tests/fixtures/source_fixture_positive.json --bootstrap-adapters --runtime-authorized
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets_negative.json --output runs/sc01-negative-t17 --source-fixture tests/fixtures/source_fixture_negative.json --bootstrap-adapters --runtime-authorized
```

Result:

```text
Positive:
- compile-context requested_version=0.8.20
- slither.compiler_selection.current_solc_version=0.8.20
- slither.compiler_selection.status=current_matches_requested
- slither.status=completed
- final_status=runtime_completed

Negative:
- slither.compiler_selection.status=current_matches_requested
- initializeMarket().state_write_signals=["balances", "totalDeposits"]
- source_truth_rejected
- foundry_allowed=false
```

Slither compiler cache/provisioning smoke after PT-024.T18:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets_positive.json --output runs/sc01-positive-t18 --source-fixture tests/fixtures/source_fixture_positive.json --bootstrap-adapters --runtime-authorized
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets_negative.json --output runs/sc01-negative-t18 --source-fixture tests/fixtures/source_fixture_negative.json --bootstrap-adapters --runtime-authorized
```

Result:

```text
Positive:
- slither.compiler_selection.provisioning.status=current_matches_requested
- install_attempted=false
- installed_versions recorded from solc-select cache
- final_status=runtime_completed

Negative:
- provisioning.status=current_matches_requested
- install_attempted=false
- source_truth_rejected
- foundry_allowed=false
```

Safety:

`--allow-solc-install` is opt-in only. Default runs never download compiler
binaries and never call `solc-select use`.

## PT-025.T01B Explorer Source Resolver Wiring

Commands:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.design_runtime.test_provider_adapters -v
python -m unittest tests.design_runtime.test_phases -v
```

Result:

```text
test_provider_adapters: 15 tests passed.
test_phases: 10 tests passed.
```

Coverage:

- `ExplorerSourceResolver` maps `ExplorerContractContext` into
  `SourceResolution`.
- Compiler version, source files, ABI and proxy context are preserved.
- Without `--source-fixture`, bootstrap wiring instantiates
  `EtherscanV2ExplorerAdapter` and passes the configured cache directory.
- No live API call was run in this session because `ETHERSCAN_API_KEY` was not
  set in the shell.

Real smoke command once key is loaded:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets-curated-real-5.json --output runs/sc01-curated-real-5 --bootstrap-adapters
```

Real smoke result with `ETHERSCAN_API_KEY` loaded from
`C:\Users\PC\Desktop\Vassago\.env`:

```text
First run:
  executed_count=45
  failed_count=2
  status=stopped
  error: phase 05 source_truth regex error

Fix:
  sc01_source._is_user_funded_accounting regex group corrected.
  Added regression:
  test_public_normal_behavior_handles_plain_assignment_without_regex_error.

Resume:
  executed_count=12
  skipped_count=43
  failed_count=0
  status=completed
```

Per-target result:

```text
ETH EntryPoint v0.6:
  source=resolved etherscan_v2
  contract=EntryPoint
  solc=0.8.17
  slither=completed slither_python
  queue_count=3
  final=blocked_no_runtime_ready

BSC PancakeSwap MasterChefV2:
  source=resolved etherscan_v2
  contract=MasterChefV2
  solc=0.6.12
  slither=completed slither_python
  queue_count=4
  final=blocked_no_runtime_ready

Base Uniswap v4 PoolManager:
  source=resolved etherscan_v2
  contract=PoolManager
  solc=0.8.26
  slither=completed slither_python
  queue_count=4
  final=blocked_no_runtime_ready

ETH Safe Singleton 1.3.0:
  source=resolved etherscan_v2
  contract=GnosisSafe
  solc=0.7.6
  slither=completed slither_python
  queue_count=2
  final=blocked_no_runtime_ready

ETH USDC FiatTokenProxy:
  source=resolved etherscan_v2
  contract=FiatTokenProxy
  solc=0.4.24
  slither=failed solc_version_cache_missing
  queue_count=2
  final=blocked_no_runtime_ready
```

Full validation after fix:

```text
python -m unittest discover -s tests: 62 tests passed.
python -m vassago_contract_runtime.cli check: passed 5/5.
git diff --check: passed, CRLF warnings only.
```

No-key graceful smoke:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets-curated-real-5.json --output runs/sc01-curated-real-5-no-key-smoke --bootstrap-adapters
```

Result:

```text
executed_count=55
failed_count=0
all 5 source-manifest.json files:
  provider=etherscan_v2
  status=unresolved
  error=etherscan_api_key_missing
```

## PT-027.T01 Adversarial Fixture Regression

Command:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.design_runtime.test_phases -v
python -m unittest tests.design_runtime.test_provider_adapters -v
```

Result:

```text
test_phases: 9 tests passed.
test_provider_adapters: 14 tests passed.
```

Assertions added:

- disabled initializer with `_disableInitializers()` does not become
  source-truth verified;
- `tx.origin` authorization appears in thesis queue and guard map, but
  `foundry_allowed=false`;
- public role-admin mutation routes as `role_admin_escalation`, but
  `foundry_allowed=false`;
- public lifecycle write is rejected as `public_lifecycle`;
- none of the adversarial fixtures produces reproduced/runtime evidence.

CLI smoke:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets_adversarial.json --source-fixture tests/fixtures/source_fixture_adversarial.json --output runs/sc01-adversarial-t27 --bootstrap-adapters --runtime-authorized
```

Result:

```text
executed_count=44
failed_count=0
status=completed
```

Final reports:

```text
0x4444...4444 blocked_no_runtime_ready, foundry_allowed=false
0x5555...5555 blocked_no_runtime_ready, foundry_allowed=false
0x6666...6666 blocked_no_runtime_ready, foundry_allowed=false
0x7777...7777 blocked_no_runtime_ready, foundry_allowed=false
```

## Not Allowed As Test Evidence

- LLM text answer.
- Static-only candidate.
- Old artifact without current run manifest.
- Explorer UI screenshot alone.
- Foundry compile-only without runtime execution.

## PT-027.T02 Final Curated Real Smoke

Command:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets-curated-real-5.json --output runs/sc01-curated-real-5-v4 --bootstrap-adapters
```

Result:

```text
executed_count=55
failed_count=0
status=completed
```

Artifact checks:

```text
ETH EntryPoint:
  selected_source_file=contracts/core/EntryPoint.sol
  source=resolved etherscan_v2
  slither=completed slither_python
  final=blocked_no_runtime_ready

BSC MasterChefV2:
  selected_source_file=contracts/MasterChefV2.sol
  source=resolved etherscan_v2
  slither=completed slither_python
  final=blocked_no_runtime_ready

Base PoolManager:
  selected_source_file=lib/v4-core/src/PoolManager.sol
  solc_remaps include solmate/=lib/v4-core/lib/solmate/
  source=resolved etherscan_v2
  slither=completed slither_python
  final=blocked_no_runtime_ready

ETH GnosisSafe:
  selected_source_file=contracts/GnosisSafe.sol
  source=resolved etherscan_v2
  slither=completed slither_python
  final=blocked_no_runtime_ready

ETH FiatTokenProxy:
  selected_source_file=FiatTokenProxy.sol
  source=resolved etherscan_v2
  slither=completed slither_python
  final=blocked_no_runtime_ready
```

Regression/gates after the fixes:

```text
python -m unittest discover -s tests: 63 tests passed.
python -m vassago_contract_runtime.cli check: passed 5/5.
git diff --check: passed, CRLF warnings only.
```

Important interpretation:

- The real read-only source/compile/Slither path is now validated for this
  curated sample.
- No target produced `runtime_ready_count > 0`.
- No target produced `foundry_allowed=true`.
- This is not vulnerability evidence; it is pipeline validation.

## PT-027.T03 20-Contract Curated Real Smoke

Command:

```powershell
$envFile='C:\Users\PC\Desktop\Vassago\.env'
# loaded ETHERSCAN_API_KEY into process without printing it
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets-curated-real-20.json --output runs/sc01-curated-real-20-v8 --bootstrap-adapters --allow-solc-install
```

Result:

```text
executed_count=220
failed_count=0
status=completed
```

Artifact checks from `runs/sc01-curated-real-20-v8`:

```text
targets=20
source_resolved=20
slither_completed=20
final_blocked_no_runtime_ready=20
foundry_allowed=0
runtime_ready_total=0
queue_total=13
source_truth_reviews_total=13
source_truth_rejected=13
```

Source-truth rejection classifications:

```text
transparent_proxy_admin_path=3
public_lifecycle=2
caller_funded_accounting=2
public_factory_or_pool_creation=2
caller_scoped_operator=1
token_approval_operator=1
protocol_pool_initializer=1
initialized_eip1967_proxy=1
```

Focused tests run before the v8 smoke:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.design_runtime.test_sc01_source -v
python -m unittest tests.design_runtime.test_phases -v
python -m unittest tests.design_runtime.test_provider_adapters -v
```

Observed result:

```text
test_sc01_source: 13 tests passed.
test_phases: 11 tests passed.
test_provider_adapters: 16 tests passed.
```

Interpretation:

- The 20-contract smoke validates source resolution, compile context,
  remapping inference and Slither for the curated sample.
- It also validates that broad SC01 candidates are terminalized before
  Foundry when source truth shows normal proxy/protocol/token behavior.
- It does not prove a vulnerability and intentionally produced no runtime
  evidence.

## PT-027.T05 Historical SC01 Curated Runtime

Focused tests before the historical runtime smoke:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.design_runtime.test_sc01_source tests.design_runtime.test_phases
python -m unittest tests.design_runtime.test_provider_adapters
```

Observed result:

```text
test_sc01_source + test_phases: 25 passed
test_provider_adapters: 16 passed
```

Runtime smoke:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets-sc01-historical-6.json --output runs/sc01-historical-6-v4-runtime --bootstrap-adapters --allow-solc-install --runtime-authorized
```

Observed result:

```text
executed_count=66
failed_count=0
source_resolved=6
slither_completed=5
source_truth_verified_total=1
runtime_ready_total=1
foundry_allowed=1
compile_passed=1
runtime_completed=1
runtime_failed=0
```

Reproduced local case:

```text
target=BadgerDAO WarRoomGatedProxy
predicate=After an unauthorized caller invokes initialize(), hasRole(DEFAULT_ADMIN_ROLE, caller) is true.
measured_delta=hasRole(DEFAULT_ADMIN_ROLE, unauthorized caller) changes false to true
evidence_status=runtime_local
no_broadcast=true
```

Blocked cases:

- Audius: proxy/governance implementation-state mapper missing.
- Nomad: bridge root/proof mapper missing; Slither failed for this source.
- Furucombo: delegatecall/proxy-storage mapper missing.
- Alchemix: keeper actor/delta mapper missing.
- Wormhole: implementation initializer/UUPS context mapper missing.

## PT-027.T06 Audius Proxy Storage Collision Base

Focused regression:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.design_runtime.test_sc01_source
python -m unittest tests.design_runtime.test_phases
```

Observed result:

```text
test_sc01_source: 17 passed
test_phases: 11 passed
```

Live historical run:

```powershell
# loaded ETHERSCAN_API_KEY from C:\Users\PC\Desktop\Vassago\.env without printing it
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets-sc01-historical-6.json --output runs/sc01-historical-6-v9-audius-privileged-writes-live --bootstrap-adapters --allow-solc-install --runtime-authorized
```

Observed result:

```text
executed_count=66
failed_count=0
status=completed
```

Audius artifact checks:

```text
source_status=resolved
proxy_implementation=0x1c91af03a390b4c619b444425b3119e553b5b44b
implementation_source_status=resolved
implementation_contract=Governance
uups_review=source_truth_rejected/custom_proxy_admin_path
proxy_collision_review=source_truth_blocked_proxy_side_verified
initializer_privileged_writes=6
remaining_blockers=proxy_delegatecall_initializer_calldata_required, measurable_proxy_state_delta_required
foundry_allowed=false
```

Badger sanity check from the same run:

```text
assertion-result.status=passed
evidence_status=runtime_local
measured_delta=hasRole(DEFAULT_ADMIN_ROLE, unauthorized caller) changes false to true
```

Interpretation:

- Audius is now a source-backed proxy-collision readiness candidate, not a
  runtime reproduction.
- The run also proves the UUPS false route is rejected cleanly for Audius.
- Runtime Foundry remains blocked for Audius until delegated initializer
  calldata and measurable proxy-state delta are generated by a dedicated
  mapper.

## PT-027.T07 Audius Proxy-Collision Runtime Mapper

Focused regression:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.design_runtime.test_sc01_source tests.design_runtime.test_phases tests.design_runtime.test_provider_adapters
python -m vassago_contract_runtime.cli check
```

Observed:

```text
focused tests=45 passed
check.status=passed
check.failed_count=0
```

First live runtime attempt:

```text
runs/sc01-historical-6-v10-audius-runtime
Audius compile_status=compile_failed
reason=Solidity address literal checksum error for lower-case Audius proxy address
```

Fix:

- render Audius proxy literal as checksummed
  `0x4DEcA517D6817B6510798b7328F2314d3003AbAC`;
- redact `--fork-url` in `FoundryRunResult.to_json()`.

Validated historical fork run:

```powershell
# loaded ETHERSCAN_API_KEY and VASSAGO_FORK_RPC_* from C:\Users\PC\Desktop\Vassago\.env without printing values
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets-sc01-historical-6.json --output runs/sc01-historical-6-v11-audius-runtime --bootstrap-adapters --allow-solc-install --runtime-authorized
```

Observed:

```text
run_id=RUN-c3c0ace00102
executed_count=66
failed_count=0
Audius target_id=CT-3f08e02c1bef
source_truth_verified_count=1
foundry_allowed=true
compile_status=compile_only_passed
runtime_status=runtime_completed
assertion-result.status=passed
evidence_status=runtime_local
no_broadcast=true
```

Foundry output:

```text
Ran 1 test for test/VassagoSC01Harness.t.sol:VassagoSC01Harness
[PASS] testAudiusProxyInitializerReplayChangesGuardian() (gas: 43312)
1 tests passed, 0 failed, 0 skipped
```

Artifact safety:

```text
foundry.command includes --fork-url <redacted-rpc-url>
ETHERSCAN_API_KEY not found in Audius target artifacts
VASSAGO_FORK_RPC_FALLBACK_ETH_URL not found in Audius target artifacts
```

Interpretation:

- Audius is locally reproduced on a historical fork for the proxy storage
  collision / initializer replay thesis.
- This remains `runtime_local`, not a current live severity claim.

## PT-027.T08/T09 Impact Review + Wormhole Context

Focused regression:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.design_runtime.test_sc01_source tests.design_runtime.test_phases tests.design_runtime.test_sc01_impact
python -m vassago_contract_runtime.cli check
```

Observed:

```text
focused tests=32 passed
check.status=passed
check.failed_count=0
```

Audius impact review:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli impact-review --run runs/sc01-historical-6-v11-audius-runtime --target-id CT-3f08e02c1bef
```

Observed:

```text
status=completed
impact_review_id=AIR-148fb9a383d8
verdict=historical_reproduced_critical
severity_posture=critical_historical_do_not_claim_live_without_current_state_review
```

Artifact:

```text
runs/sc01-historical-6-v11-audius-runtime/targets/CT-3f08e02c1bef/phases/11_impact_review/sc01-impact-review.json
```

Wormhole source-truth rerun:

```powershell
$env:PYTHONPATH='src'
$env:ETHERSCAN_API_KEY = 'cache-only-placeholder'
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets-sc01-historical-6.json --output runs/sc01-historical-6-v14-wormhole-source-truth --bootstrap-adapters --source-cache-dir runs/sc01-historical-6-v11-audius-runtime/_cache/etherscan-v2
```

Observed:

```text
executed_count=66
failed_count=0
Wormhole queue_count=3
Wormhole source_truth_verified_count=1
Wormhole evidence_kind=wormhole_uninitialized_implementation
Wormhole foundry_allowed=false
```

Interpretation:

- Audius has impact-review wording suitable for severity discussion, but no
  current live risk claim.
- Wormhole implementation context is now recognized and source-truth verified.
- Wormhole runtime remains blocked until VM payload, malicious initializer
  implementation and dedicated runner exist.

## PT-027.T10 Wormhole Runtime Runner

Focused regression:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.design_runtime.test_sc01_source tests.design_runtime.test_phases
```

Observed:

```text
32 tests passed
```

Coverage:

- `evaluate_wormhole_uninitialized_implementation()` now returns:
  - `runtime_runner=wormhole_implementation_runtime`;
  - `missing_proof_pieces=[]`;
  - `fork_block_number=13818843`.
- `render_sc01_harness()` emits a Wormhole-specific interface-only harness for
  proxy `0x98f3c9e6E3fAce36bAAd05FE09d375Ef1464288B`.
- phase test confirms the target reaches:
  - `source_truth_verified_count=1`;
  - `foundry_allowed=true`;
  - fake runtime `runtime_completed`.

Real smoke:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli run-design `
  --design sc01-access `
  --targets tests/fixtures/targets-sc01-historical-6.json `
  --output runs/sc01-historical-6-v15-wormhole-runtime `
  --bootstrap-adapters `
  --source-cache-dir runs/sc01-historical-6-v11-audius-runtime/_cache/etherscan-v2 `
  --runtime-authorized
python -m vassago_contract_runtime.cli impact-review `
  --run runs/sc01-historical-6-v16-wormhole-runtime `
  --target-id CT-24700f446e33
```

Precondition:

- `VASSAGO_FORK_RPC_URL` or `VASSAGO_FORK_RPC_FALLBACK_ETH_URL` must point to
  an archive-capable Ethereum RPC that serves block `13_818_843`.

Observed real smoke:

```text
run_dir=runs/sc01-historical-6-v16-wormhole-runtime
run_id=RUN-07be0359b9b4
executed_count=66
failed_count=0
Wormhole compile_status=compile_only_passed
Wormhole runtime_status=runtime_completed
Wormhole assertion.status=passed
Wormhole evidence_status=runtime_local
Wormhole no_broadcast=true
Impact review verdict=historical_reproduced_critical
Current live risk=not_claimed
```

Foundry output excerpt:

```text
[PASS] testWormholeImplementationInitializerReplayExecutesMaliciousDelegatecall()
```

Artifact:

```text
runs/sc01-historical-6-v16-wormhole-runtime/targets/CT-24700f446e33/phases/11_impact_review/sc01-impact-review.json
```

Interpretation:

- Wormhole is locally reproduced on a historical fork for the implementation
  initializer / malicious upgrade path.
- This is historical critical context, not a current live severity claim.
- The harness includes the selfdestruct path, but the assertion measures a
  storage marker written during malicious delegatecall because code deletion is
  transaction-final and hardfork-dependent.

## PT-027.T11 Nomad Bridge Root/Proof Runtime Mapper

Focused regression:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.design_runtime.test_sc01_source tests.design_runtime.test_phases tests.design_runtime.test_sc01_impact
```

Observed:

```text
37 tests passed
```

Full checks during implementation:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests
python -m vassago_contract_runtime.cli check
git diff --check
```

Observed before docs update:

```text
83 tests passed
check status=passed
git diff --check passed with CRLF warnings only
```

Real smoke:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets-sc01-historical-6.json --output runs/sc01-historical-6-v18-nomad-runtime --bootstrap-adapters --source-cache-dir runs/sc01-historical-6-v11-audius-runtime/_cache/etherscan-v2 --runtime-authorized
python -m vassago_contract_runtime.cli impact-review --run runs/sc01-historical-6-v18-nomad-runtime --target-id CT-05f41610b129
```

Observed Nomad runtime:

```text
run_dir=runs/sc01-historical-6-v18-nomad-runtime
run_id=RUN-881c3ae4d0ba
executed_count=66
failed_count=0
Nomad source_truth_verified_count=1
Nomad rejected thesis=uninitialized_implementation_proxy
Nomad verified thesis=bridge_root_proof_validation
Nomad compile_status=compile_only_passed
Nomad runtime_status=runtime_completed
Nomad assertion.status=passed
Nomad evidence_status=runtime_local
Impact review verdict=historical_reproduced_critical
Current live risk=not_claimed
```

Foundry output excerpt:

```text
[PASS] testNomadProcessesUnprovenForgedMessageOnHistoricalFork()
```

Artifact:

```text
runs/sc01-historical-6-v18-nomad-runtime/targets/CT-05f41610b129/phases/11_impact_review/sc01-impact-review.json
```

Interpretation:

- Nomad is locally reproduced on a historical fork for bridge root/proof
  message-authentication bypass.
- This is historical critical context, not a current live severity claim.
- The current implementation source resolves as fixed; runtime proof depends
  on the pinned historical fork.

## PT-027.T12/T13 Furucombo + Alchemix Historical Runtime Mappers

Focused regression:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.design_runtime.test_sc01_source
```

Observed:

```text
23 tests passed
```

Real smoke:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets-sc01-historical-6.json --output runs/sc01-historical-6-v22-furucombo-alchemix-runtime --source-cache-dir runs/source-cache-v20 --bootstrap-adapters --runtime-authorized
python -m vassago_contract_runtime.cli impact-review --run runs/sc01-historical-6-v22-furucombo-alchemix-runtime --target-id CT-2964504f0811
python -m vassago_contract_runtime.cli impact-review --run runs/sc01-historical-6-v22-furucombo-alchemix-runtime --target-id CT-4b5839bd1d37
```

Observed Furucombo:

```text
target_id=CT-2964504f0811
compile_status=compile_only_passed
runtime_status=runtime_completed
assertion.status=passed
Foundry=[PASS] testFurucomboWhitelistedProxyDelegatecallDrainsVictimAllowance()
impact verdict=historical_reproduced_critical
current live risk=not_claimed
no_broadcast=true
```

Observed Alchemix:

```text
target_id=CT-4b5839bd1d37
compile_status=compile_only_passed
runtime_status=runtime_completed
assertion.status=passed
Foundry=[PASS] testAlchemixGenericKeeperCanTriggerLowMinHarvest()
impact verdict=historical_reproduced_high_context
current live risk=not_claimed
no_broadcast=true
```

## PT-027.T15 Nomad Root/Proof Sidecars

Focused regression:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.design_runtime.test_sc01_source tests.design_runtime.test_phases
```

Observed:

```text
38 tests passed
```

Coverage added:

- `build_nomad_root_proof_analysis()` returns root/proof model, message plan,
  runtime assertions and current-state review checklist.
- Phase 05 emits `nomad-root-proof-analysis.json`.
- Phase 06 emits `bridge-state-review.json`.
- Nomad no longer uses `local_initializer_*` status labels in on-chain state.
- `current_state_review.live_claim_allowed=false` remains explicit.

Real sidecar smoke without runtime:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets-sc01-historical-6.json --output runs/sc01-historical-6-v23-nomad-sidecars --source-cache-dir runs/source-cache-v20 --bootstrap-adapters
```

Observed:

```text
run_id=RUN-0ded12db3e58
status=completed
failed_count=0
Nomad target_id=CT-05f41610b129
nomad-root-proof-analysis.status=historical_runtime_ready
bridge-state-review.status=historical_fork_state_ready_current_live_not_claimed
admin-state.status=protocol_specific_admin_state_not_required
current_state_review.live_claim_allowed=false
final_status=runtime_ready_pending_local_execution
runtime_status=blocked_runtime_authorization_required
```

## PT-027.T16 Nomad Current-State Read-Only Review

Focused unit:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.design_runtime.test_sc01_source
```

Observed:

```text
25 tests passed
```

Real read-only current-state command:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli current-state-review --run runs/sc01-historical-6-v23-nomad-sidecars --target-id CT-05f41610b129
```

Observed:

```text
review_id=CSR-f8f008ef218c
current_block_number=25372508
implementation=0x7f221a1850c12b57fed1f0831dd25399a13b68c2
localDomain()=6648936
acceptableRoot(bytes32(0))=false
confirmAt(bytes32(0))=1
messages(forged_message_hash)=0x0000000000000000000000000000000000000000000000000000000000000000
verdict=current_default_root_path_rejected
current_live_risk=not_indicated_by_current_default_root_probe
no_broadcast=true
```

Interpretation:

- The historical Nomad fork exploit remains reproduced historically.
- The current deployment rejects the same default-root predicate checked here.
- No asset-moving recipient runtime is required for this specific path because
  the root gate blocks before recipient execution.

## PT-027.T17 Bridge Current-Path Review

Focused unit:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.design_runtime.test_sc01_bridge_review
```

Observed:

```text
5 tests passed
```

Full regression:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests
```

Observed:

```text
94 tests passed
```

Repository gate:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli check
git diff --check
```

Observed:

```text
check status=passed
git diff --check: only CRLF warning for cli.py
```

Real static/read-only sidecar smoke:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli bridge-current-review --run runs/sc01-historical-6-v23-nomad-sidecars --target-id CT-05f41610b129
```

Observed:

```text
review_id=BCR-3ed18c3eb479
protocol=nomad_replica
active_path_count=4
ready_for_state_review_count=1
blocked_path_count=3
root_proof_verifier=candidate_ready_for_state_review
processed_message_replay=blocked_reader_missing
escrow_supply_delta=blocked_reader_missing
recipient_asset_moving=blocked_asset_delta_missing
current_live_risk=not_claimed
```

## PT-028.T01-T03 Historical Exploit Corpus

Purpose:

- replace random-only target selection with a blind historical exploit corpus;
- keep detector inputs separate from scoring labels;
- seed 100 cases across five families.

Commands:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli historical-corpus-report --targets-output designs/historical-exploits/targets-blind-100.json
python -m unittest tests.design_runtime.test_historical_corpus tests.design_runtime.test_sc01_bridge_review
```

Observed:

```text
historical-corpus-report status=completed
case_count=100
target_count=100
duplicate_target_count=0
invalid_cases=[]
target_export.status=completed
focused tests: 7 passed
```

Corpus balance:

```text
sc01_access_control=20
bridge_message_auth=20
oracle_accounting=20
reentrancy_token=20
proxy_upgrade_signature=20
```

Next validation:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests
python -m vassago_contract_runtime.cli check
git diff --check
```

Next benchmark:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets designs/historical-exploits/targets-blind-100.json --output runs/sc01-historical-blind-100-v1 --source-cache-dir runs/source-cache-v20 --bootstrap-adapters
```

Actual blind benchmark run:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets designs\historical-exploits\targets-blind-100.json --output runs\sc01-historical-blind-100-v1 --source-cache-dir runs\source-cache-historical-100 --bootstrap-adapters
python -m vassago_contract_runtime.cli resume --run runs\sc01-historical-blind-100-v1 --source-cache-dir runs\source-cache-historical-100 --bootstrap-adapters
```

Observed:

```text
first pass: executed_count=1091 failed_count=1 skipped_count=9 status=stopped
failure: CT-bd324a5e31c2 phase=01_dossier WinError 5 manifest write
resume: executed_count=10 failed_count=0 skipped_count=1090 status=completed
final phase count: completed=1100
```

Scoring tests:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.design_runtime.test_historical_scoring tests.design_runtime.test_historical_corpus
```

Observed:

```text
4 tests passed
```

Scoring smoke:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli historical-corpus-score --run runs\sc01-historical-6-v23-nomad-sidecars --manifest designs\historical-exploits\manifest.json --limit 2 --output-dir runs\_score-smoke-limit2
```

Observed:

```text
status=completed
historical-corpus-score.json written
historical-corpus-score.md written
```

Blind benchmark score:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli historical-corpus-score --run runs\sc01-historical-blind-100-v1 --manifest designs\historical-exploits\manifest.json --output-dir runs\sc01-historical-blind-100-v1\historical-corpus-score
```

Observed:

```text
case_count=100
scored_count=100
candidate_count=67
none_count=32
runtime_ready_count=1
runtime_count=0
```

Runtime follow-up for HEC-031:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets runs\_selected\hec-031-target.json --output runs\sc01-historical-blind-hec031-runtime-v1 --source-cache-dir runs\source-cache-historical-100 --bootstrap-adapters --runtime-authorized
python -m vassago_contract_runtime.cli historical-corpus-score --run runs\sc01-historical-blind-hec031-runtime-v1 --manifest designs\historical-exploits\manifest.json --benchmark-id HEC-031 --output-dir runs\sc01-historical-blind-hec031-runtime-v1\historical-corpus-score-hec031
```

## PT-028.T07 stage-failure report

Focused validation:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.design_runtime.test_historical_stage_report tests.design_runtime.test_historical_scoring
```

Observed:

```text
Ran 4 tests
OK
```

Real report command:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli historical-stage-report --run runs\sc01-historical-blind-100-v1 --manifest designs\historical-exploits\manifest.json --output-dir runs\sc01-historical-blind-100-v1\historical-stage-failure
```

Observed summary:

```text
case_count=100
candidate_count=67
runtime_ready_count=1
runtime_count=0
04_no_thesis_candidate=32
05_source_truth_not_verified=67
09_runtime_authorization_pending=1
```

Artifacts:

- `runs/sc01-historical-blind-100-v1/historical-stage-failure/historical-stage-failure-report.json`
- `runs/sc01-historical-blind-100-v1/historical-stage-failure/historical-stage-failure-report.md`

Candidate priority:

```text
proxy_upgrade_signature=17
oracle_accounting=15
reentrancy_token=14
sc01_access_control=11
bridge_message_auth=10
```

## PT-028.T08 proxy/upgrade mapper

Focused regression:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.design_runtime.test_sc01_proxy_upgrade tests.design_runtime.test_sc01_source
```

Observed:

```text
Ran 32 tests
OK
```

Mapper integration smoke over previously resolved blind-100 artifacts:

```powershell
$env:PYTHONPATH='src'
# Python one-shot script imported _review_queue_item and replayed source-truth
# over runs/sc01-historical-blind-100-v1 for the 20 proxy_upgrade_signature cases.
```

Observed classes:

```text
source_truth_verified_runtime_blocked/uninitialized_proxy_or_implementation_initializer=1
source_truth_rejected/transparent_proxy_admin_path=4
source_truth_rejected/disable_initializers_present=3
source_truth_blocked_runtime_specific_mapper/proxy_implementation_source_missing=5
source_truth_blocked_runtime_specific_mapper/role_admin_graph_required=2
source_truth_blocked_runtime_specific_mapper/initializer_without_measurable_critical_write=2
```

Fresh isolated family run:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli historical-corpus-report --manifest designs\historical-exploits\manifest.json --family proxy_upgrade_signature --targets-output runs\_selected\proxy-upgrade-t08-targets.json
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets runs\_selected\proxy-upgrade-t08-targets.json --output runs\sc01-historical-proxy-upgrade-t08-v1 --source-cache-dir runs\source-cache-historical-100 --bootstrap-adapters
python -m vassago_contract_runtime.cli historical-stage-report --run runs\sc01-historical-proxy-upgrade-t08-v1 --manifest designs\historical-exploits\manifest.json --family proxy_upgrade_signature --output-dir runs\sc01-historical-proxy-upgrade-t08-v1\historical-stage-failure
```

Observed:

```text
run-design executed_count=220 failed_count=0 target_count=20
stage report: 04_no_thesis_candidate=20
```

Interpretation:

- the mapper works when source-truth receives proxy candidates;
- the isolated fresh run exposed a routing/acquisition gap before source-truth;
- next task is `PT-028.T09`, not Foundry.

## PT-028.T09 proxy thesis acquisition

Focused regression:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.design_runtime.test_sc01_proxy_acquisition tests.design_runtime.test_sc01_proxy_upgrade tests.design_runtime.test_phases
```

Observed:

```text
Ran 24 tests
OK
```

Dynamic acquisition replay over resolved blind-100 proxy-upgrade artifacts:

```powershell
$env:PYTHONPATH='src'
# Python one-shot script imported build_proxy_upgrade_candidates and replayed
# it over runs/sc01-historical-blind-100-v1 for the 20 proxy_upgrade_signature cases.
```

Observed:

```text
dynamic acquisition candidates in 9/20 cases
uninitialized_implementation_proxy=8
uups_weak_auth=4
role_admin_escalation=2
```

Fresh family-only run:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets runs\_selected\proxy-upgrade-t08-targets.json --output runs\sc01-historical-proxy-upgrade-t09-v1 --source-cache-dir runs\source-cache-historical-100 --bootstrap-adapters
python -m vassago_contract_runtime.cli historical-stage-report --run runs\sc01-historical-proxy-upgrade-t09-v1 --manifest designs\historical-exploits\manifest.json --family proxy_upgrade_signature --output-dir runs\sc01-historical-proxy-upgrade-t09-v1\historical-stage-failure
```

Observed:

```text
run-design executed_count=220 failed_count=0 target_count=20
source-manifest.status=unresolved on sampled target
stage report: 04_no_thesis_candidate=20
```

Interpretation:

- T09 works when source/ABI/proxy context exists;
- fresh family reruns still need resolver/cache reliability work;
- next task is `PT-028.T10`.

## PT-028.T10 source resolver/cache reliability

Focused regression:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.design_runtime.test_provider_adapters
```

Observed:

```text
Ran 19 tests
OK
```

Coverage added:

- Etherscan V2 source context can be read from cache without an API key and
  without invoking the network transport.
- Cache miss without an API key reports `etherscan_api_key_missing` and
  `cache_hit=false` instead of silently losing source/proxy context.

Fresh proxy-upgrade family rerun:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets runs\_selected\proxy-upgrade-t08-targets.json --output runs\sc01-historical-proxy-upgrade-t10-v1 --source-cache-dir runs\source-cache-historical-100 --bootstrap-adapters
python -m vassago_contract_runtime.cli historical-stage-report --run runs\sc01-historical-proxy-upgrade-t10-v1 --manifest designs\historical-exploits\manifest.json --family proxy_upgrade_signature --output-dir runs\sc01-historical-proxy-upgrade-t10-v1\historical-stage-failure
```

Observed:

```text
run-design executed_count=220 failed_count=0 target_count=20
source_resolved=20 source_unresolved=0 cache_hits=20
stage report:
  04_no_thesis_candidate=3
  05_source_truth_not_verified=16
  07_proof_pieces_incomplete=1
  runtime_ready_count=0
```

Interpretation:

- T10 fixes the resolver/cache blocker from T09;
- no Foundry/runtime is implied: the remaining blockers are source-truth and
  proof-piece completeness for proxy-upgrade candidates.

Observed:

```text
runtime status=runtime_completed
assertion status=passed
evidence_status=runtime_local
score case_count=1 runtime_count=1
```
