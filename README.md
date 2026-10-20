# Contract Analysis Runtime

A contract-first runtime for repeatable, resumable security campaigns with explicit evidence states.

## Features

- Campaign designs define ordered phases, inputs, outputs and gates.
- Run manifests and artifact indexing support resumable execution.
- Evidence states distinguish static candidates, compilation and local runtime reproduction.

## Stack

Python · JSON manifests · YAML designs · optional Slither/Foundry adapters · MCP interface

Versioned run, target and artifact manifests are persisted as files. Private run output and historical runtime directories are excluded.

## Getting started

Python >=3.11. Use the src/ layout declared in pyproject.toml; inspect the design and evidence policy before running any campaign. Start with tests/design_runtime/test_models.py.

## How it works

```text
Contract target → versioned design → gated phases → indexed artifacts → evidence-qualified report
```

## Current limitations

Only the focused offline model suite was run here. No deployed-contract campaign, fork, compiler provisioning or transaction was executed. A static finding is not a reproduced vulnerability.

## Tests

```console
python -m unittest discover -s tests/design_runtime -p test_models.py -v
```

These checks use offline fixtures or controlled backends.

## License

Project-authored source code is licensed under the [MIT License](LICENSE). Third-party components and datasets retain their respective rights and licenses.
