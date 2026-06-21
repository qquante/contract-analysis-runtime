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
