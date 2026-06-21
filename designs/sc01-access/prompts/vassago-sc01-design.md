---
name: vassago-sc01-design
description: Hermes skill for the clean Vassago SC01 design runtime. It calls vassago_design_run first, then reads sc01-final-report.json with vassago_artifact_read.
---

# VASSAGO SC01 Design Runtime Agent

Use this skill when the task is to run the new contract-first SC01 campaign
runtime, not the legacy fine-grained Vassago SC01 tool chain.

## Runtime MCP

Hermes server name:

```text
vassago_contract_runtime
```

Configured stdio command:

```text
C:\Users\PC\Desktop\vassago-contract-runtime\scripts\hermes-vassago-contract-runtime-mcp.cmd
```

Expected tool prefix in Hermes:

```text
mcp_vassago_contract_runtime_
```

Available tools:

- `mcp_vassago_contract_runtime_vassago_design_run`
- `mcp_vassago_contract_runtime_vassago_design_resume`
- `mcp_vassago_contract_runtime_vassago_artifact_read`

## Hard Rules

- Start with `mcp_vassago_contract_runtime_vassago_design_run` unless the user
  gives an existing run directory.
- For existing runs, use `mcp_vassago_contract_runtime_vassago_design_resume`.
- Read canonical final reports with
  `mcp_vassago_contract_runtime_vassago_artifact_read`.
- Do not use shell for design execution while the MCP tools are available.
- Do not call legacy fine-grained SC01 tools unless the new runtime is missing
  or the user explicitly asks for legacy fallback.
- Do not broadcast transactions.
- Do not use key material, raw signed transactions or live mutation methods.
- Do not claim a vulnerability from static-only, candidate-only, compile-only
  or dry-run output.
- Do not create ad hoc JSON or Markdown reports.

## Default Run Call

For a local fixture smoke:

```json
{
  "design": "sc01-access",
  "targets_path": "tests/fixtures/targets.json",
  "output": "runs/sc01-fixture-bootstrap",
  "bootstrap_adapters": true,
  "source_fixture": "tests/fixtures/source_fixture.json",
  "resume": true
}
```

For inline targets:

```json
{
  "design": "sc01-access",
  "targets": [
    {"chain": "eth", "address": "0x1111111111111111111111111111111111111111"}
  ],
  "output": "runs/sc01-design-smoke",
  "bootstrap_adapters": true,
  "resume": true
}
```

## Final Report Read

After `vassago_design_run`, capture `run_dir` and `run_id`.

Read:

```text
vassago://runs/{run_id}/targets/{target_id}/phases/10_final_report/sc01-final-report.json
```

with:

```json
{
  "run": "<run_dir>",
  "uri": "vassago://runs/<run_id>/targets/<target_id>/phases/10_final_report/sc01-final-report.json"
}
```

## Interpret Status

- `blocked_no_runtime_ready`: safe stop; do not run Foundry.
- `runtime_ready_pending_local_execution`: runtime could be authorized by the
  user, but it has not run yet.
- `compile_only_passed_runtime_blocked`: compile-only context exists; runtime
  proof is absent.
- `foundry_allowed=false`: Foundry runtime is blocked.
- `evidence_status=static_only`: no exploit proof.

## Final Answer Shape

Return:

```json
{
  "sc01_design_status": "completed | completed_with_failures | failed",
  "run_dir": "...",
  "run_id": "...",
  "targets_processed": 0,
  "final_reports": [],
  "counts": {
    "source_truth_verified": 0,
    "runtime_ready": 0,
    "foundry_allowed": 0
  },
  "evidence_position": {
    "no_broadcast": true,
    "no_key_material": true,
    "no_evidence_promotion": true
  },
  "next_actions": []
}
```

Escalate to `vassago-sc01-access` only after `sc01-final-report.json` exists
and asks for deeper access-control analysis.
