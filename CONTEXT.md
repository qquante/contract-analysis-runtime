# Context

## Mission

Build a clean campaign runtime for Vassago that can run security designs against
deployed smart contracts in a repeatable, resumable and evidence-safe way.

The immediate use case is SC01 Access Control, but the runtime must be generic
enough to later host SC02-SC10 designs.

## Primary Domain Terms

### ContractTarget

The unit of work:

```text
(chain, address)
```

A target can be enriched with ABI, source, proxy context, bytecode, storage,
logs, balances, tx history, compile context and local proof artifacts.

### Design

A versioned campaign definition. Example: `sc01-access`.

A Design contains phases, required inputs, artifacts, gates and final report
rules.

### Phase

A deterministic step in a Design. A Phase has:

- id;
- name;
- inputs;
- outputs;
- gate behavior;
- resume behavior;
- status.

### Run

One execution of a Design over one or more ContractTargets.

Every Run must have a `run-manifest.json`.

### Artifact

Structured output written by a Phase. Artifacts are indexed by run, target and
phase.

### Thesis

A concrete vulnerability hypothesis. For SC01 examples:

- uninitialized implementation/proxy;
- weak UUPS authorization;
- Safe module/fallback abuse;
- bridge endpoint/source validation;
- role admin/self-admin escalation;
- hook/callback caller validation;
- arbitrary sender/from.

### ProofPiece

Required proof element before runtime:

- source-truth guard gap;
- actor model;
- codable args;
- measurable reader;
- measurable delta;
- explicit predicate;
- compile-only pass.

### RuntimeProof

Local/fork deterministic execution proving or rejecting the thesis.

## Non-Goals

- No chain broadcast.
- No generic shell MCP.
- No evidence promotion from LLM output.
- No static finding promoted to reproduced issue.
- No random large batch before campaign metrics exist.

## Relationship To Original Vassago

The old Vassago repo contains many working adapters and tools. This repo should
not copy the entire tool surface. It should import or reimplement only behind
deep Interfaces:

- SourceResolver Adapter;
- Explorer Adapter;
- Slither Adapter;
- Foundry Adapter;
- ArtifactStore Adapter;
- Corpus Adapter.
