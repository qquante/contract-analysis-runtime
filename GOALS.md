# Goals

## G-001 - Contract-first campaign runtime

Status: active; runtime foundation and bootstrap adapters implemented through phase 09 plus final report.

Build a resumable Design runtime around `ContractTarget(chain, address)`.

Acceptance:

- `run-manifest.json` exists. Done.
- each target has phase status. Done.
- resume does not recompute completed phases. Done in unit tests.
- all artifacts are indexed. Initial ArtifactStore done.
- CLI can run/resume a design. Done for dry-run and bootstrap local phases
  00/01/03.
- real read-only Explorer source resolution is wired into bootstrap phase 01
  when no `--source-fixture` is supplied.

## G-002 - SC01 Access Control v1 design

Status: active.

Implement the first Design: `sc01-access`.

Acceptance:

- it runs through all planned phases;
- phases 00 through 08 and 10 have local skeleton adapters;
- it can stop safely when proof pieces are missing;
- it can run compile-only harness when ready through a Foundry adapter;
- it can run Foundry local only when runtime gate is satisfied. Done for local
  positive fixture with explicit runtime authorization.
- phase 02 can prefer normalized Slither IR over heuristic source parsing when
  compile context and IR are available.

## G-003 - Evidence integrity

Status: active.

Keep candidate, static, formal, compile-only and runtime evidence separated.

Acceptance:

- no static finding can become `reproduced_runtime`;
- LLM proposals cannot set evidence status;
- runtime proof requires local deterministic execution.
- local positive fixture now exercises deterministic Foundry runtime.
- real Slither Python API can fill static IR, select installed solc versions
  through compile context, and inspect/provision the solc-select cache behind
  explicit opt-in.
- curated real smoke `runs/sc01-curated-real-20-v8` validates read-only
  Etherscan V2 source resolution plus Slither Python on 20 real contracts
  without promoting any candidate to runtime evidence.
- source-truth now terminalizes broad non-SC01 candidates before Foundry:
  transparent proxy admin paths, initialized EIP-1967 proxy context, protocol
  pool/factory creation, token approval/operator APIs and caller-funded
  accounting/lifecycle behavior.
- historical Wormhole runner is implemented as a local/fork-only harness behind
  the same compile/runtime gates. Its archive-fork smoke and impact review are
  complete, with current live risk `not_claimed`.
- historical Nomad root/proof mapper is implemented as a local/fork-only bridge
  message-authentication harness behind the same compile/runtime gates. Its
  archive-fork smoke and impact review are complete, with current live risk
  `not_claimed`.
- Nomad now also emits root/proof and current-state-review sidecars so
  historical reproduction cannot be confused with a live exploitability claim.
- Nomad current-state review now rejects the historical default-root path in
  current state with read-only calls:
  `acceptableRoot(bytes32(0)) == false`.
- Bridge current-path review now routes future live-risk work by path
  (`endpoint_source_validation`, `processed_message_replay`,
  `root_proof_verifier`, `escrow_supply_delta`, `recipient_asset_moving`)
  while keeping `current_live_risk=not_claimed`.

## G-004 - Small top-level agent Interface

Status: active.

The top-level VASSAGO/Hermes agent should call campaign-level tools, not dozens
of fine-grained builders.

Acceptance:

- top-level agent uses `run_design`, `resume_design`, `artifact_read`. Done as
  internal tool contracts in `src/vassago_contract_runtime/tools/`;
- local MCP stdio exposes only campaign-level tools. Done in
  `src/vassago_contract_runtime/mcp/`;
- Hermes skill `vassago-sc01-design` points to the local MCP server and starts
  with `vassago_design_run`. Done locally and prompt versioned in repo;
- fine-grained adapters are internal to phases or specialist subagents.

## G-005 - SC01 corpus as executable knowledge

Status: active.

Convert SC01 docs and historical patterns into normalized corpus records.

Acceptance:

- YAML records exist under `designs/sc01-access/corpus/`;
- each record has motifs, negative signals, required evidence and runtime runner;
- corpus matches are hypotheses only. Done for phase 03 skeleton.
- first adversarial records exist for `tx_origin_authorization`,
  `role_admin_escalation` and `public_lifecycle_noise`.
- remaining records still needed for Safe/module, bridge endpoint/source,
  ERC4337 validator and metamorphic guard edge cases.
- Audius-style `proxy_storage_collision_reinitializer` is represented as corpus
  knowledge and has a historical local/fork reproduction plus conservative
  impact review.
- Wormhole-style uninitialized implementation context is represented as
  source-truth knowledge and now has a dedicated VM/payload runtime harness.
- Nomad-style bridge root/proof validation failure is represented as corpus
  knowledge and now has a dedicated historical fork runtime harness.
- Furucombo-style trusted handler plus nested delegatecall proxy-storage
  confusion is represented as corpus knowledge and has a dedicated historical
  fork runtime harness.
- Alchemix-style generic keeper parameter access-control is represented as
  corpus knowledge and has a dedicated historical fork runtime harness.

## G-008 - Historical exploit benchmark corpus

Status: active.

Goal:

- stop relying on random target samples as the main signal source;
- maintain a blind corpus of historical exploit targets with scoring-only
  ground truth;
- use the corpus to measure false positives, false negatives, source/import
  failures and missing protocol mappers.

Current state:

- PT-028 first seed has `100` cases balanced across access-control,
  bridge/message-auth, oracle/accounting, reentrancy/token and
  proxy/upgrade/signature.
- `designs/historical-exploits/targets-blind-100.json` is ready for the next
  blind benchmark.
- `historical-corpus-score` can score a completed run after the blind phase.
- Current blind benchmark `runs/sc01-historical-blind-100-v1` is complete:
  `67` candidate-only, `32` none and `1` runtime-ready.
- Current runtime follow-up `runs/sc01-historical-blind-hec031-runtime-v1`
  reproduced HEC-031/Nomad locally on a historical fork.
- `historical-stage-report` now explains where the blind cases stopped:
  `32` no-thesis, `67` source-truth-not-verified and `1`
  runtime-authorization-pending.
- Current candidate priority is proxy/upgrade/signature first, then
  oracle/accounting, reentrancy/token, SC01 access control and bridge/message
  auth.
- Proxy/upgrade family reruns now hydrate source/proxy context from
  `runs/source-cache-historical-100`: `20/20` sources resolved with
  `cache_hit=true` in `runs/sc01-historical-proxy-upgrade-t10-v1`.
- `PT-028.T11` added proxy semantic dossiers/proposals/validation in phase
  `05_source_truth`: `proxy-upgrade-dossier.json`,
  `proxy-upgrade-semantic-proposals.json` and
  `proxy-upgrade-proposal-validation.json`.
- `PT-028.T12` added proxy impact review:
  `proxy-upgrade-impact-review.json`. The current proxy-upgrade family run
  `runs/sc01-historical-proxy-upgrade-t12-v2` has `runtime_ready_count=1`,
  target `CT-5c096b36038c`, and `compile_only_passed`.
- The current proxy/upgrade blocker is runtime execution environment, not
  source/proxy context: an Optimism fork RPC and explicit runtime authorization
  are required before any local Foundry runtime.

Non-goal:

- do not turn historical case names, addresses or labels into detector rules.
- do not claim current live exploitability from historical metadata.
