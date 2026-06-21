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
