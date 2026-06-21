# Goals

## G-001 - Contract-first campaign runtime

Status: active.

Build a resumable Design runtime around `ContractTarget(chain, address)`.

Acceptance:

- `run-manifest.json` exists.
- each target has phase status.
- resume does not recompute completed phases.
- all artifacts are indexed.

## G-002 - SC01 Access Control v1 design

Status: planned.

Implement the first Design: `sc01-access`.

Acceptance:

- it runs through all planned phases;
- it can stop safely when proof pieces are missing;
- it can run compile-only harness when ready;
- it can run Foundry local only when runtime gate is satisfied.

## G-003 - Evidence integrity

Status: active.

Keep candidate, static, formal, compile-only and runtime evidence separated.

Acceptance:

- no static finding can become `reproduced_runtime`;
- LLM proposals cannot set evidence status;
- runtime proof requires local deterministic execution.

## G-004 - Small top-level agent Interface

Status: planned.

The top-level VASSAGO/Hermes agent should call campaign-level tools, not dozens
of fine-grained builders.

Acceptance:

- top-level agent uses `run_design`, `resume_design`, `artifact_read`;
- fine-grained adapters are internal to phases or specialist subagents.

## G-005 - SC01 corpus as executable knowledge

Status: planned.

Convert SC01 docs and historical patterns into normalized corpus records.

Acceptance:

- YAML records exist under `designs/sc01-access/corpus/`;
- each record has motifs, negative signals, required evidence and runtime runner;
- corpus matches are hypotheses only.
