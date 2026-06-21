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
| Unit | `python -m unittest discover -s tests` | all pass; current: 26 expected after corpus/source slice |
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
Ran 26 tests
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

Smoke:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets.json --source-fixture tests/fixtures/source_fixture.json --output <temp> --bootstrap-adapters
```

Result:

```text
RunStatus=completed
SourceStatus=resolved
FunctionCount=2
CandidateStatus=candidate_only
CandidateCount=2
ThesisIds=uninitialized_implementation_proxy,uups_weak_auth
```

## Not Allowed As Test Evidence

- LLM text answer.
- Static-only candidate.
- Old artifact without current run manifest.
- Explorer UI screenshot alone.
- Foundry compile-only without runtime execution.
