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
| Unit | `python -m unittest discover -s tests` | all pass; current: 33 expected after source-truth/state/tooling slice |
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
Ran 46 tests
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

## Not Allowed As Test Evidence

- LLM text answer.
- Static-only candidate.
- Old artifact without current run manifest.
- Explorer UI screenshot alone.
- Foundry compile-only without runtime execution.
