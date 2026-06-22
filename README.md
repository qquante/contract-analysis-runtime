# Vassago Contract Runtime

Contract-first campaign runtime for Vassago.

This repository is a clean implementation track for the part that became too
wide in the original Vassago repo: running repeatable, resumable security
campaigns against deployed smart contracts.

Primary target unit:

```text
ContractTarget(chain, address)
```

The runtime enriches that target with ABI, verified source, bytecode, proxy
context, storage/readers, logs, token balances, tx history, compile context and
local-only proof artifacts.

This repo does not replace the old Vassago immediately. It should first produce
a small, clean design runtime, then import/adapt proven modules from Vassago
behind narrow interfaces.

## Core Rule

No evidence is invented.

Statuses must stay separated:

- `static_only`
- `read_only_real`
- `candidate`
- `blocked`
- `compile_only_passed`
- `not_reproduced`
- `reproduced_runtime`
- `human_review_required`

`reproduced_runtime` requires deterministic local/fork execution. No broadcast.

## First Design

The first design is:

```text
designs/sc01-access/
```

It implements OWASP SC01 Access Control as a contract-first campaign:

```text
00 intake
01 dossier
02 semantic surface
03 corpus motifs
04 thesis acquisition
05 source truth
06 on-chain state
07 proof pieces
08 compile-only
09 runtime Foundry local
10 final report
```

## Expected Commands

Current working commands:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests
python -m vassago_contract_runtime.cli check
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets.json --output runs/sc01-smoke --dry-run
python -m vassago_contract_runtime.cli resume --run runs/sc01-smoke --dry-run
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets.json --output runs/sc01-bootstrap --bootstrap-adapters
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets.json --source-fixture tests/fixtures/source_fixture.json --output runs/sc01-fixture-bootstrap --bootstrap-adapters
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets_positive.json --source-fixture tests/fixtures/source_fixture_positive.json --output runs/sc01-positive-local-runtime --bootstrap-adapters --runtime-authorized
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets_adversarial.json --source-fixture tests/fixtures/source_fixture_adversarial.json --output runs/sc01-adversarial-local --bootstrap-adapters --runtime-authorized
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets-curated-real-5.json --output runs/sc01-curated-real-5 --bootstrap-adapters
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets-curated-real-20.json --output runs/sc01-curated-real-20 --bootstrap-adapters --allow-solc-install
python -m vassago_contract_runtime.cli mcp --stdio
```

Current real curated baseline:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets-curated-real-20.json --output runs/sc01-curated-real-20-v8 --bootstrap-adapters --allow-solc-install
```

Expected current result:

```text
executed_count=220
failed_count=0
all 20 source-manifest.json files resolved through etherscan_v2
all 20 access-surface.json.slither.status values are completed
13 source-truth reviews, all rejected by negative policy
all 20 final reports are blocked_no_runtime_ready
all 20 foundry_allowed values are false
```

Hermes wrapper:

```powershell
C:\Users\PC\Desktop\vassago-contract-runtime\scripts\hermes-vassago-contract-runtime-mcp.cmd
```

Bootstrap execution exists for phase 00 intake, phase 01 dossier skeleton,
phase 02 semantic surface, phase 03 corpus motifs, phase 04 thesis acquisition,
phase 05 source truth skeleton, phase 06 on-chain state skeleton, phase 07
proof pieces, phase 08 compile-only skeleton, phase 09 local Foundry runtime
and phase 10 final report. With
`--source-fixture`, phase 01 indexes local ABI/source, phase 02 writes static
semantic sidecars, phase 03 produces `candidate_only` corpus thesis candidates,
phase 04 queues them for source truth, phase 05 blocks until stronger source
truth exists, phase 06 writes provider-required state sidecars, phase 07 keeps
`foundry_allowed=false` until proof pieces are complete, phase 08 skips Forge
when not compile-ready, phase 09 requires `foundry_allowed=true`,
`compile_only_passed` and explicit `--runtime-authorized`, and phase 10 writes
the final report. No broadcast path is wired.

Without `--source-fixture`, bootstrap mode now resolves phase 01 source through
the read-only Etherscan V2 Explorer adapter. Set `ETHERSCAN_API_KEY` in the
environment. Source responses are cached under `<output>/_cache/etherscan-v2`
by default; pass `--source-cache-dir <path>` to override.

Phase 02 prefers normalized Slither IR when compile context and IR are
available. Without IR it falls back to the local ABI/source heuristic and marks
the degraded `extraction_source` in `access-surface.json`. Slither CLI JSON is
detector context only. Bootstrap mode now wires `PythonSlitherAdapter`, which
uses `slither-analyzer` when installed to fill normalized IR. If local solc
cannot compile the source pragma, the artifact records
`slither_python_analysis_failed` and keeps the heuristic fallback. Compile
context selects installed compiler versions through `SOLC_VERSION`; it does not
download missing compilers by default. Pass `--allow-solc-install` only in a
controlled setup/smoke when you explicitly want `solc-select install <version>`
for missing compilers. The runtime never calls `solc-select use`.

The positive fixture under `tests/fixtures/source_fixture_positive.json` is a
local regression case for the historical UUPS uninitialized implementation
pattern. It is not a live-contract severity claim.

Historical runtime runners currently implemented:

- Audius proxy storage collision / delegated initializer replay:
  local/fork-only, no broadcast, fork block `15201793`;
- Wormhole uninitialized implementation / guardian VM upgrade replay:
  local/fork-only, no broadcast, fork block `13818843`, interface-only harness
  that reads the historical implementation from the proxy EIP-1967 slot.

The adversarial fixture set under
`tests/fixtures/source_fixture_adversarial.json` covers disabled initializer,
`tx.origin` authorization, public role-admin mutation and public lifecycle
noise. It exists to prevent false promotion and hardcoded name matching before
real-contract smoke runs.

## Agent Tool Contracts

The internal tool registry lives in `src/vassago_contract_runtime/tools/`.
Current canonical contracts:

- `vassago_design_run`;
- `vassago_design_resume`;
- `vassago_artifact_read`.

These contracts call the same `runtime_api.py` path as the CLI. They are
local-only, no-shell, no-broadcast and do not expose phase internals to the
top-level agent. MCP stdio is the next layer and should wrap these contracts,
not duplicate the runtime.

## MCP stdio

Local MCP stdio is available through:

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli mcp --stdio
```

Supported MCP methods:

- `initialize`;
- `notifications/initialized`;
- `ping`;
- `tools/list`;
- `tools/call`.

Only three tools are exposed:

- `vassago_design_run`;
- `vassago_design_resume`;
- `vassago_artifact_read`.

## Hermes Skill

Local Hermes skill:

```text
C:\Users\PC\AppData\Local\hermes\skills\domain\vassago-sc01-design\SKILL.md
```

Versioned prompt source:

```text
designs/sc01-access/prompts/vassago-sc01-design.md
```

The skill should call `mcp_vassago_contract_runtime_vassago_design_run` first
and then read `sc01-final-report.json` with
`mcp_vassago_contract_runtime_vassago_artifact_read`.
