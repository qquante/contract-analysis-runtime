# Goals

## G-001 - Contract-first campaign runtime

Status: active; runtime foundation and bootstrap adapters implemented through phase 08 plus final report.

Build a resumable Design runtime around `ContractTarget(chain, address)`.

Acceptance:

- `run-manifest.json` exists. Done.
- each target has phase status. Done.
- resume does not recompute completed phases. Done in unit tests.
- all artifacts are indexed. Initial ArtifactStore done.
- CLI can run/resume a design. Done for dry-run and bootstrap local phases
  00/01/03.

## G-002 - SC01 Access Control v1 design

Status: active.

Implement the first Design: `sc01-access`.

Acceptance:

- it runs through all planned phases;
- phases 00 through 08 and 10 have local skeleton adapters;
- it can stop safely when proof pieces are missing;
- it can run compile-only harness when ready through a Foundry adapter;
- it can run Foundry local only when runtime gate is satisfied.

## G-003 - Evidence integrity

Status: active.

Keep candidate, static, formal, compile-only and runtime evidence separated.

Acceptance:

- no static finding can become `reproduced_runtime`;
- LLM proposals cannot set evidence status;
- runtime proof requires local deterministic execution.

## G-004 - Small top-level agent Interface

Status: active.

The top-level VASSAGO/Hermes agent should call campaign-level tools, not dozens
of fine-grained builders.

Acceptance:

- top-level agent uses `run_design`, `resume_design`, `artifact_read`. Done as
  internal tool contracts in `src/vassago_contract_runtime/tools/`;
- local MCP stdio exposes only campaign-level tools. Done in
  `src/vassago_contract_runtime/mcp/`;
- fine-grained adapters are internal to phases or specialist subagents.

## G-005 - SC01 corpus as executable knowledge

Status: planned.

Convert SC01 docs and historical patterns into normalized corpus records.

Acceptance:

- YAML records exist under `designs/sc01-access/corpus/`;
- each record has motifs, negative signals, required evidence and runtime runner;
- corpus matches are hypotheses only. Done for phase 03 skeleton.
