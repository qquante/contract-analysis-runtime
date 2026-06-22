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
