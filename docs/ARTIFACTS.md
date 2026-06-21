# Artifacts

All artifacts live under a run directory:

```text
runs/<run-id>/
  run-manifest.json
  targets/<target-id>/
    target-manifest.json
    phases/<phase-id>/
      phase-manifest.json
      artifacts...
```

Artifact URI:

```text
vassago://runs/{run_id}/targets/{target_id}/phases/{phase_id}/{artifact_name}
```

Rules:

- artifacts must be content-hashed;
- artifacts must include producer phase;
- artifacts must include created timestamp;
- stale artifacts cannot drive Foundry;
- secret redaction is mandatory for RPC URLs and API keys.

## Current SC01 Bootstrap Artifacts

Phase `00_intake`:

- `target-manifest.json`
- `scope-policy.json`

Phase `01_dossier`:

- `scan-dossier.json`
- `function-index.json`
- `source-manifest.json`
- `compile-context.json`
- `protocol-fingerprint.json`

Phase `02_semantic_surface`:

- `access-surface.json`
- `semantic-map.json`
- `guard-map.json`
- `state-write-map.json`
- `role-graph.json`

Phase `03_corpus_motifs`:

- `sc01-corpus-matches.json`
- `sc01-thesis-candidates.json`

Phase `04_thesis_acquisition`:

- `sc01-thesis-queue.json`
- `sc01-acquisition-report.json`

Phase `05_source_truth`:

- `sc01-source-truth.json`

Phase `06_onchain_state`:

- `admin-state.json`
- `proxy-state.json`
- `role-state.json`

Phase `07_proof_pieces`:

- `sc01-proof-piece-state.json`
- `sc01-exploit-hypotheses.json`
- `sc01-runtime-ready.json`

Phase `08_compile_only`:

- `VassagoSC01Harness.t.sol`
- `compile-result.json`

Phase `10_final_report`:

- `sc01-final-report.json`
- `sc01-final-report.md`

`sc01-thesis-candidates.json` is candidate-only routing context. It is never
runtime evidence and cannot enable Foundry by itself.
