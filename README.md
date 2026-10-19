# Contract Analysis Runtime

> **Local private review:** publication is paused. See [security review and remaining release conditions](docs/SECURITY_REVIEW.md). Local fixes have not been pushed.


A contract-first runtime for repeatable, resumable security campaigns with explicit evidence states.

![review](https://img.shields.io/badge/review-private-374151) ![primary](https://img.shields.io/badge/primary-Python-2563EB) [![LinkedIn](https://img.shields.io/badge/LinkedIn-Douglas%20Silva-0A66C2?logo=linkedin&logoColor=white)](https://www.linkedin.com/in/douglas-silva-data-analyst/)

[Overview](#overview) · [Architecture](#architecture) · [Setup](#setup) · [Validation](#validation) · [Roadmap](#roadmap) · [Review notes](docs/REVIEW.md)

## Overview

- Campaign designs define ordered phases, inputs, outputs and gates.
- Run manifests and artifact indexing support resumable execution.
- Evidence states distinguish static candidates, compilation and local runtime reproduction.

**Technology:** Python · JSON manifests · YAML designs · optional Slither/Foundry adapters · MCP interface

**Persistence and data:** Versioned run, target and artifact manifests are persisted as files. Private run output and historical runtime directories are excluded.

## Architecture

```text
Contract target → versioned design → gated phases → indexed artifacts → evidence-qualified report
```

| Location | Review focus |
| --- | --- |
| [`src/vassago_contract_runtime/design_runtime`](src/vassago_contract_runtime/design_runtime) | Source/configuration inspected for scope and structure |
| [`designs/sc01-access/design.yaml`](designs/sc01-access/design.yaml) | Source/configuration inspected for scope and structure |
| [`docs/ARTIFACTS.md`](docs/ARTIFACTS.md) | Source/configuration inspected for scope and structure |
| [`tests/design_runtime/test_models.py`](tests/design_runtime/test_models.py) | Source/configuration inspected for scope and structure |

Internal package and module names are retained where changing them would affect imports or compatibility. This descriptive repository name does not imply a completed package/API migration.

## Setup

Python >=3.11. Use the src/ layout declared in pyproject.toml; inspect the design and evidence policy before running any campaign. Start with tests/design_runtime/test_models.py.

Start from an isolated environment. Use `.env.example` when present and inspect the configuration loader: an example file is not necessarily loaded automatically. Runtime databases, real account sessions and private credentials are not bundled. Live integration prerequisites are separate from local tests.

## Validation

Static parsing checked 76 Python files and 13 strict JSON files. Python syntax errors: 0; JSON errors: 0. The selected offline suite passed.

```console
python -m unittest discover -s tests/design_runtime -p test_models.py -v
```

These results apply to the selected checks on the preparation copy. They do not establish deployment readiness, full coverage, live provider availability or measured performance. CI definitions, when present under `docs/ci-templates/`, are inactive review templates; no remote CI badge is claimed.

## Limits and current status

Only the focused offline model suite was run here. No deployed-contract campaign, fork, compiler provisioning or transaction was executed. A static finding is not a reproduced vulnerability.

This private snapshot is for code and portfolio review. Generated runtime material and unreviewed binary assets may be excluded. [Review notes](docs/REVIEW.md) record preparation scope, findings and outstanding validation.

## Roadmap

- [ ] Run remaining offline design/runner tests.
- [ ] Package an entirely local fixture campaign.
- [ ] Validate optional analysis and local-fork adapters in isolated environments.

## History and attribution

31 existing commits were retained after path/content filtering. Original authors and author/committer dates were retained; commit hashes may change. Upstream commits are not presented as new work by the maintainer.

No open-source license is granted by this preparation. A license and attribution review is required before public redistribution.

## Maintainer and feedback

Douglas de Oliveira Silva · [GitHub](https://github.com/qquante) · [LinkedIn](https://www.linkedin.com/in/douglas-silva-data-analyst/)

For this private review, report reproducible issues with a minimal fixture and the exact check output. Keep account data, credentials and generated sensitive reports out of issues and commits. Existing contribution guidelines apply where present.

**Topics:** `python`, `smart-contracts`, `security-analysis`, `developer-tools`, `mcp`, `reproducibility`
