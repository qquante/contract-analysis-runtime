# Execution Map

## Lane A - Runtime Foundation

```text
PT-023.T01 DesignSpec / PhaseSpec / GateSpec - done 2026-06-21
PT-023.T02 RunManifest / TargetManifest / ArtifactIndex - done 2026-06-21
PT-023.T03 PhaseRunner with resume - done 2026-06-21
PT-023.T04 CLI skeleton - done 2026-06-21
PT-023.T05 check command - done 2026-06-21
```

## Lane B - SC01 Design

```text
PT-024.T01 designs/sc01-access/design.yaml - done 2026-06-21
PT-024.T02 phase 00 intake - done 2026-06-21
PT-024.T03 phase 01 dossier - done 2026-06-21 skeleton with fixture source support
PT-024.T04 phase 02 semantic surface - done 2026-06-21 skeleton
PT-024.T05 phase 03 corpus motifs - done 2026-06-21 skeleton
PT-024.T06 phase 04 thesis acquisition - done 2026-06-21 skeleton
PT-024.T07 phase 05 source truth - done 2026-06-21 skeleton
PT-024.T08 phase 06 on-chain state - done 2026-06-21 skeleton
PT-024.T09 phase 07 proof pieces - done 2026-06-21 skeleton
PT-024.T10 phase 08 compile-only - done 2026-06-21 skeleton
PT-024.T11 phase 09 runtime Foundry local - done 2026-06-21 local-only gated adapter
PT-024.T12 phase 10 final report - done 2026-06-21 skeleton
PT-024.T13 source-backed positive verification - done 2026-06-21
PT-024.T14 source-backed negative verification - done 2026-06-21
PT-024.T15 Slither IR source extraction - done 2026-06-21 normalized IR first, heuristic fallback
PT-024.T16 real Slither Python API IR extraction - done 2026-06-21
PT-024.T17 Slither compiler/version selection - done 2026-06-21
PT-024.T18 Slither compiler cache/provisioning - done 2026-06-21 controlled solc-select cache
PT-024.T19 Slither failure summary by target - planned if curated smoke needs it
```

## Lane C - Adapters

```text
PT-025.T01 SourceResolver interface - done 2026-06-21 interface plus null and fixture adapters
PT-025.T02 Explorer interface - done 2026-06-21 interface plus Etherscan V2 cache adapter
PT-025.T01B Explorer-backed SourceResolver wiring - done 2026-06-21
PT-025.T03 Slither interface - done 2026-06-21 interface plus subprocess adapter
PT-025.T04 Foundry interface - done 2026-06-21 interface plus null adapter
PT-025.T04B Foundry subprocess adapter - done 2026-06-21 local-only compile/runtime gate
PT-025.T05 Corpus interface - done 2026-06-21 interface plus local design corpus adapter
```

## Lane D - Agent/MCP

```text
PT-026.T01 tool contracts for run_design/resume_design/artifact_read - done 2026-06-21
PT-026.T02 MCP stdio local - done 2026-06-21
PT-026.T03 Hermes skill vassago-sc01-design - done 2026-06-21
PT-026.T04 A2A card for SC01 design runner
```

## Lane E - Validation

```text
PT-027.T01 local SC01 adversarial fixture expansion - done first slice 2026-06-21
PT-027.T01B remaining adversarial/metamorphic fixtures
PT-027.T02 SC01 smoke 5 curated real contracts - done 2026-06-21, run baseline runs/sc01-curated-real-5-v4
PT-027.T03 SC01 smoke 20 curated contracts - done 2026-06-21, run baseline runs/sc01-curated-real-20-v8
PT-027.T04 high-signal target acquisition before any larger batch
PT-027.T05 historical SC01 curated runtime suite - done 2026-06-21, run baseline runs/sc01-historical-6-v4-runtime
PT-027.T06 Audius proxy storage collision base - done 2026-06-21, run baseline runs/sc01-historical-6-v9-audius-privileged-writes-live
PT-027.T07 Audius proxy collision runtime mapper - next
```

## Current Next Up

1. Use `runs/sc01-historical-6-v4-runtime` as the current historical runtime
   evidence baseline, `runs/sc01-historical-6-v9-audius-privileged-writes-live`
   as the current Audius readiness baseline, and
   `runs/sc01-curated-real-20-v8` as the broad curated false-positive baseline.
2. Implement `PT-027.T07`: Audius proxy collision runtime mapper that derives
   proxy fallback initializer calldata and measurable proxy-state deltas.
3. Implement high-signal target acquisition instead of broad random expansion:
   weak `_authorizeUpgrade`, initialized proxy state impact, concrete
   role-admin graph, Safe/AA/module sidecars with measurable deltas.
4. Build mappers for the remaining historical blockers: Audius governance,
   Nomad bridge root/proof, Furucombo delegatecall/proxy-storage, Alchemix
   keeper-state and Wormhole implementation/UUPS context.
5. Expand remaining local adversarial fixtures: no-op guard, post-check guard,
   Safe/module, bridge endpoint/source and ERC4337 validator.
6. Add per-target Slither/source summary only if a larger real smoke shows
   repeated compiler/import misses.
7. Implement PT-026.T04 A2A card after the design runtime remains stable.
