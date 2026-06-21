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
