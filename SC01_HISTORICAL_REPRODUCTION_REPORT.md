# SC01 Historical Reproduction Report

Updated: 2026-06-22.

Scope:

- local Foundry/fork reproduction only;
- no broadcast;
- no private key;
- no transaction sent on-chain;
- no automatic current live exploitability claim.

## Summary

The SC01 design runtime now has five historical, project-specific local/fork
reproductions:

| Case | Run | Target id | Runtime | Assertion | Impact posture |
|---|---|---:|---|---|---|
| Audius governance proxy | `runs/sc01-historical-6-v11-audius-runtime` | `CT-3f08e02c1bef` | `runtime_completed` | `passed` | `historical_reproduced_critical` |
| Wormhole core bridge | `runs/sc01-historical-6-v16-wormhole-runtime` | `CT-24700f446e33` | `runtime_completed` | `passed` | `historical_reproduced_critical` |
| Nomad Replica | `runs/sc01-historical-6-v18-nomad-runtime` | `CT-05f41610b129` | `runtime_completed` | `passed` | `historical_reproduced_critical` |
| Furucombo proxy v1.0.0 | `runs/sc01-historical-6-v22-furucombo-alchemix-runtime` | `CT-2964504f0811` | `runtime_completed` | `passed` | `historical_reproduced_critical` |
| Alchemix Harvester | `runs/sc01-historical-6-v22-furucombo-alchemix-runtime` | `CT-4b5839bd1d37` | `runtime_completed` | `passed` | `historical_reproduced_high_context` |

## Evidence Boundaries

These results mean:

- the runtime harness compiled;
- the runtime gate was satisfied;
- Foundry executed locally against a pinned fork where applicable;
- the assertion passed;
- the result is evidence for historical/local reproduction.

These results do not mean:

- the target is currently exploitable;
- funds are currently at risk;
- patched deployments are vulnerable;
- a bug bounty report can claim live severity without current-state review.

## Case Notes

### Audius

- Bug class: `proxy_storage_collision_reinitializer_governance_takeover`.
- Local predicate: proxy-delegated initializer replay changes privileged
  governance state.
- Impact review:
  `runs/sc01-historical-6-v11-audius-runtime/targets/CT-3f08e02c1bef/phases/11_impact_review/sc01-impact-review.json`.

### Wormhole

- Bug class: `wormhole_uninitialized_implementation_guardian_takeover`.
- Local predicate: historical implementation context can be initialized with
  attacker guardian and reach guardian-governed upgrade path.
- Impact review:
  `runs/sc01-historical-6-v16-wormhole-runtime/targets/CT-24700f446e33/phases/11_impact_review/sc01-impact-review.json`.

### Nomad

- Bug class: `nomad_bridge_root_proof_message_authentication_bypass`.
- Local predicate: historical Replica accepts and processes an unproven forged
  message through root/proof validation.
- Impact review:
  `runs/sc01-historical-6-v18-nomad-runtime/targets/CT-05f41610b129/phases/11_impact_review/sc01-impact-review.json`.

### Furucombo

- Bug class: `furucombo_delegatecall_proxy_storage_confusion`.
- Local predicate: public `batchExec` delegates to historically whitelisted
  Aave V2 proxy, initializes its implementation in Furucombo proxy storage
  context, then executes attacker code with victim token allowance context.
- Fork block: `11_940_499`.
- Foundry test:
  `testFurucomboWhitelistedProxyDelegatecallDrainsVictimAllowance`.
- Impact review:
  `runs/sc01-historical-6-v22-furucombo-alchemix-runtime/targets/CT-2964504f0811/phases/11_impact_review/sc01-impact-review.json`.
- Important correction: `0xA013AfbB9A92cEF49e898C87C060e6660E050569`
  is the post-mortem redeployed proxy, not the vulnerable historical proxy used
  for reproduction. The historical fixture now uses
  `0x17e8Ca1b4798B97602895f63206afCd1Fc90Ca5f`.

### Alchemix

- Bug class: `alchemix_keeper_parameter_access_control`.
- Local predicate: the Harvester accepts configured automation caller and
  caller-supplied harvest parameters, matching the historical generic keeper
  actor issue model.
- Fork block: `17_650_000`.
- Foundry test:
  `testAlchemixGenericKeeperCanTriggerLowMinHarvest`.
- Impact review:
  `runs/sc01-historical-6-v22-furucombo-alchemix-runtime/targets/CT-4b5839bd1d37/phases/11_impact_review/sc01-impact-review.json`.

## Reproduction Commands

```powershell
$env:PYTHONPATH='src'
python -m vassago_contract_runtime.cli run-design --design sc01-access --targets tests/fixtures/targets-sc01-historical-6.json --output runs/sc01-historical-6-v22-furucombo-alchemix-runtime --source-cache-dir runs/source-cache-v20 --bootstrap-adapters --runtime-authorized
python -m vassago_contract_runtime.cli impact-review --run runs/sc01-historical-6-v22-furucombo-alchemix-runtime --target-id CT-2964504f0811
python -m vassago_contract_runtime.cli impact-review --run runs/sc01-historical-6-v22-furucombo-alchemix-runtime --target-id CT-4b5839bd1d37
```

The command requires:

- `ETHERSCAN_API_KEY` for fresh source acquisition when cache is empty;
- `VASSAGO_FORK_RPC_URL` or `VASSAGO_FORK_RPC_FALLBACK_ETH_URL` with archive
  access for historical fork blocks.

## Next Work

1. Keep these five historical cases as regression fixtures.
2. Add current-state review tooling separately if live exploitability needs to
   be assessed.
3. Continue SC01 expansion through target acquisition and protocol-specific
   mappers, not random batches.
4. For new SC01 claims, require the same chain:
   source truth -> proof pieces -> compile-only -> local runtime -> impact
   review.
