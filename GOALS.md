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
- Audius-style `proxy_storage_collision_reinitializer` is now represented as
  corpus knowledge and reaches source-backed readiness through implementation
  source/initializer/write evidence, but remains non-runtime until delegated
  initializer calldata and proxy-state delta are measurable.
