# Architecture

## Target Shape

The runtime should be built from deep Modules:

```text
DesignRuntime
  uses PhaseRunner
  uses ArtifactStore
  uses AdapterRegistry
  uses GateEngine
```

Each Module should hide implementation complexity behind a small Interface.

## Module Map

### DesignRuntime

Interface:

```python
run_design(design_id, targets, output, options)
resume_design(run_path, options)
```

Implementation:

- load design spec;
- create run manifest;
- execute phases;
- update phase status;
- enforce gates;
- write final report.

### PhaseRunner

Interface:

```python
run_phase(run, target, phase)
```

Implementation:

- read inputs;
- call phase adapter;
- validate outputs;
- write phase manifest;
- support resume.

### ArtifactStore

Interface:

```python
write_artifact(run_id, target_id, phase_id, name, payload)
read_artifact(uri)
index_artifacts(run_path)
```

Implementation:

- filesystem layout;
- content hash;
- artifact URI;
- redaction checks.

### GateEngine

Interface:

```python
evaluate_gate(gate_id, artifacts)
```

Implementation:

- compile gate;
- runtime gate;
- evidence gate.

### AdapterRegistry

Interface:

```python
get_adapter(name)
```

Implementation:

- SourceResolver Adapter;
- Explorer Adapter;
- Slither Adapter;
- Foundry Adapter;
- Corpus Adapter.

## Why This Shape

The previous Vassago flow exposed too many fine-grained tools to the agent. That
made the Interface almost as complex as the implementation.

This repo should make the campaign the Interface. The agent says:

```text
run SC01 design on these targets
```

The runtime owns the details.
