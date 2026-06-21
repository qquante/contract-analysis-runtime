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
| Unit | `python -m unittest discover -s tests` | all pass; current: 14 passed |
| Check | `python -m vassago_contract_runtime.cli check` | validates manifests/designs |
| Design dry run | `python -m vassago_contract_runtime.cli run-design --dry-run ...` | manifests only |
| Resume | `python -m vassago_contract_runtime.cli resume --run ...` | skips completed phases |
| SC01 fixture | run SC01 on local fixture | no broadcast, correct status |
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
Ran 14 tests in 0.715s
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

## Not Allowed As Test Evidence

- LLM text answer.
- Static-only candidate.
- Old artifact without current run manifest.
- Explorer UI screenshot alone.
- Foundry compile-only without runtime execution.
