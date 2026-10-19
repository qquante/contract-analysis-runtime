# Agent Instructions

Respond in Brazilian Portuguese by default.

This repo is contract-first. Do not drift into broad repo auditing unless a task
explicitly says repo-mode.

Default safety policy:

- read-only by default;
- no private keys;
- no broadcast;
- no `eth_sendRawTransaction`;
- no real transaction;
- Foundry/Anvil only local fork;
- never promote static findings to reproduced evidence;
- never use stale artifacts as proof.

Before editing:

1. Read `CONTEXT.md`.
2. Read `TASKS.md`.
3. Read `EXECUTION_MAP.md`.
4. Read the design file under `designs/<design>/design.yaml`.
5. Make small modular changes.
6. Run focused tests.
7. Update `SESSIONS.md`, `TASKS.md`, `TESTS.md`, and `EXECUTION_MAP.md` when the task changes project state.

Architecture vocabulary:

- Use `Module`, `Interface`, `Implementation`, `Depth`, `Seam`, `Adapter`,
  `Leverage`, and `Locality`.
- Prefer deep Modules with small Interfaces.
- Avoid exposing fine-grained tools to the top-level agent when a campaign phase
  can own the complexity.

Evidence vocabulary:

- `candidate`: signal only.
- `blocked`: required proof piece is missing.
- `terminal_rejected`: confirmed not exploitable by the current thesis.
- `compile_only_passed`: generated harness compiles but did not execute runtime.
- `not_reproduced`: local runtime ran and did not prove the issue.
- `reproduced_runtime`: local deterministic runtime proved a measurable delta.

Do not create or rely on ad hoc JSON outside the run/artifact manifest.
