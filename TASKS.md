# Tasks

This file is intentionally detailed. A fresh agent should be able to start from
here without reading the old Vassago conversation.

## Current Status

Repository bootstrap complete.

PT-023.T01-T03 are implemented and covered by unit tests.

## NEXT UP

1. `PT-023.T04` - implement CLI skeleton.
2. `PT-023.T05` - implement strict check.
3. `PT-024.T01` - validate `designs/sc01-access/design.yaml`.
4. `PT-024.T02` - implement phase 00 intake.

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

Status: pending.

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

## PT-023.T05 - Strict Check

Status: pending.

Implement checks:

- design yaml valid;
- no production Python file > 800 lines;
- no forbidden evidence promotion strings outside gate module;
- no secrets in tracked docs;
- no artifact path traversal.

---

# PT-024 - SC01 Access Control Design

## Summary

Implement the first contract-first Design.

## PT-024.T01 - Design Spec

Status: pending.

Files:

- `designs/sc01-access/design.yaml`
- `tests/design_runtime/test_sc01_design_spec.py`

Acceptance:

- design loads;
- phase graph is ordered;
- required artifacts are declared.

## PT-024.T02 - Phase 00 Intake

Status: pending.

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

## PT-024.T03 - Phase 01 Dossier

Status: pending.

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

## PT-024.T04 - Phase 02 Semantic Surface

Status: pending.

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

## PT-024.T05 - Phase 03 Corpus Motifs

Status: pending.

Purpose:

Use SC01 corpus records as hypothesis generators.

Outputs:

- `sc01-corpus-matches.json`;
- `sc01-thesis-candidates.json`.

Rules:

- corpus match is not evidence;
- each match must list negative signals.

## PT-024.T06 - Phase 04 Thesis Acquisition

Status: pending.

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

## PT-024.T07 - Phase 05 Source Truth

Status: pending.

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

Statuses:

- `source_truth_verified`;
- `source_truth_rejected`;
- `source_truth_blocked`.

## PT-024.T08 - Phase 06 On-Chain State

Status: pending.

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

## PT-024.T09 - Phase 07 Proof Pieces

Status: pending.

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

Status: pending.

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

Status: pending.

Purpose:

Run local fork only when runtime-ready.

Rules:

- no broadcast;
- no private key;
- no live transaction;
- local/fork only;
- fixed block where possible.

Outputs:

- `foundry-runtime-result.json`;
- `assertion-result.json`;
- `evidence.md`.

Statuses:

- `reproduced_runtime`;
- `not_reproduced`;
- `runtime_failed`;
- `inconclusive`.

## PT-024.T12 - Phase 10 Final Report

Status: pending.

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

Status: pending.

Interface:

- `resolve_source(chain, address)`.

Must support:

- Etherscan-compatible APIs;
- Sourcify;
- local fixture.

## PT-025.T02 - Explorer Adapter

Status: pending.

Interface:

- `get_logs`;
- `get_contract_creation`;
- `get_token_holdings`;
- `get_transactions`;
- `get_proxy_context`.

Must include cache and rate limit.

## PT-025.T03 - Slither Adapter

Status: pending.

Interface:

- `analyze_source_bundle`;
- `extract_ir`.

Slither IR should be primary for writes/modifiers/calls when compile context
allows.

## PT-025.T04 - Foundry Adapter

Status: pending.

Interface:

- `compile_harness`;
- `run_local_fork`.

Must enforce no broadcast.

## PT-025.T05 - Corpus Adapter

Status: pending.

Interface:

- `search_corpus(query, family)`;
- `load_record(record_id)`.

---

# PT-026 - Agent And MCP

## PT-026.T01 - Tool Contracts

Status: pending.

Tools:

- `vassago_design_run`;
- `vassago_design_resume`;
- `vassago_artifact_read`.

## PT-026.T02 - MCP stdio

Status: pending.

Local-only stdio first.

## PT-026.T03 - Hermes Skill

Status: pending.

Skill:

- `vassago-sc01-design`.

Prompt behavior:

- call `vassago_design_run`;
- read report;
- only request subagent when a phase is blocked;
- never call fine-grained tools first.

---

# PT-027 - Validation Campaigns

## PT-027.T01 - Local Fixtures

Status: pending.

Create fixtures:

- missing critical guard;
- safe public deposit;
- no-op guard;
- post-check modifier;
- uninitialized implementation;
- weak UUPS;
- Safe module;
- bridge endpoint;
- ERC4337 validator;
- role self-admin.

## PT-027.T02 - SC01 Smoke 5 Contracts

Status: pending.

Run design on 5 known contracts.

Acceptance:

- no crash;
- phase report complete;
- no false reproduced evidence.

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

# RESUME FROM HERE

Start with `PT-023.T01`.

Do not port old Vassago modules yet. Build the runtime skeleton first with fake
adapters and fixtures. Once the runner, manifest, resume and artifact index are
tested, adapt the old SC01 campaign into `designs/sc01-access` phase by phase.
