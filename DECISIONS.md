# Decisions

## D-001 - Contract-first, repo-mode secondary

Date: 2026-06-21.

Decision:

- The primary target is `ContractTarget(chain, address)`.
- Repo-mode is optional and secondary.

Reason:

- The operational goal is to scan many deployed contracts.
- ABI/source/proxy/storage/logs are enough to build most SC01 campaigns.
- Full repo is valuable when available, but cannot be required.

## D-002 - Campaign phases over tool chains

Date: 2026-06-21.

Decision:

- Expose campaign-level Interfaces to agents.
- Keep fine-grained builders inside phases.

Reason:

- Top-level agent tool sprawl caused slow, fragile flows in the old repo.
- Design phases give locality and resume.

## D-003 - Foundry as a phase

Date: 2026-06-21.

Decision:

- Foundry/Anvil/Forge runtime is phase 09 of a Design.
- It runs only when proof pieces and compile-only pass.
- It is always local/fork only.

Reason:

- Treating Foundry as a manual exception made the old flow feel permanently
  blocked.
- Treating it as a phase makes skip/run status explicit.
