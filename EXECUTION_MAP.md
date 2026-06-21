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
PT-024.T11 phase 09 runtime Foundry local - pending gated runtime adapter wiring
PT-024.T12 phase 10 final report - done 2026-06-21 skeleton
```

## Lane C - Adapters

```text
PT-025.T01 SourceResolver interface - done 2026-06-21 interface plus null and fixture adapters
PT-025.T02 Explorer interface - done 2026-06-21 interface plus Etherscan V2 cache adapter
PT-025.T03 Slither interface - done 2026-06-21 interface plus subprocess adapter
PT-025.T04 Foundry interface - done 2026-06-21 interface plus null adapter
PT-025.T04B Foundry subprocess adapter - done 2026-06-21 local-only compile/runtime gate
PT-025.T05 Corpus interface - done 2026-06-21 interface plus local design corpus adapter
```

## Lane D - Agent/MCP

```text
PT-026.T01 tool contracts for run_design/resume_design/artifact_read
PT-026.T02 MCP stdio local
PT-026.T03 Hermes skill vassago-sc01-design
PT-026.T04 A2A card for SC01 design runner
```

## Lane E - Validation

```text
PT-027.T01 unit tests for manifest/resume
PT-027.T02 fixture targets
PT-027.T03 local SC01 ground-truth campaign
PT-027.T04 smoke 5 contracts
PT-027.T05 smoke 20 contracts
PT-027.T06 only then larger batch
```

## Current Next Up

1. Implement PT-024.T11 runtime Foundry local phase only behind `foundry_allowed=true`.
2. Implement PT-026.T01 tool contracts for run/resume/artifact-read.
3. Add fixture that produces a compile-ready hypothesis for phase 08 positive coverage.
4. Keep SC01 logic as design phases, not as top-level tool sprawl.
