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
```

Bootstrap execution exists for phase 00 intake, phase 01 dossier skeleton,
phase 02 semantic surface, phase 03 corpus motifs, phase 04 thesis acquisition,
phase 05 source truth skeleton and phase 06 on-chain state skeleton. With
`--source-fixture`, phase 01 indexes local ABI/source, phase 02 writes static
semantic sidecars, phase 03 produces `candidate_only` corpus thesis candidates,
phase 04 queues them for source truth, phase 05 blocks until stronger source
truth exists, and phase 06 writes provider-required state sidecars. Phase 07+
remains dry-run until those adapters are implemented.
