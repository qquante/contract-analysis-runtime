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
```

Bootstrap execution exists for phase 00 intake and phase 01 dossier skeleton.
The remaining phases are dry-run until their adapters are implemented.
