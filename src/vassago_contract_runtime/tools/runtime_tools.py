"""Canonical Design Runtime tools for agents."""

from __future__ import annotations

from typing import Any

from vassago_contract_runtime.runtime_api import (
    read_artifact_from_payload,
    resume_design_from_payload,
    run_design_from_payload,
)

from .contracts import ToolContract, ToolRegistry


def build_runtime_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(_design_run_contract(), run_design_from_payload)
    registry.register(_design_resume_contract(), resume_design_from_payload)
    registry.register(_artifact_read_contract(), read_artifact_from_payload)
    return registry


def _base_policy() -> dict[str, Any]:
    return {
        "local_only": True,
        "no_broadcast": True,
        "no_key_material": True,
        "no_shell": True,
        "static_never_promotes": True,
    }


def _design_run_contract() -> ToolContract:
    return ToolContract(
        name="vassago_design_run",
        version="v1",
        description="Run a versioned Vassago design against contract targets through the resumable phase runtime.",
        aliases=("design_run", "run_design"),
        effects=("filesystem_write_artifacts",),
        policy=_base_policy(),
        input_schema={
            "type": "object",
            "required": ["design", "output"],
            "properties": {
                "design": {"type": "string"},
                "targets": {"type": "array", "items": {"type": "object"}},
                "targets_path": {"type": "string"},
                "output": {"type": "string"},
                "dry_run": {"type": "boolean", "default": False},
                "bootstrap_adapters": {"type": "boolean", "default": True},
                "source_fixture": {"type": "string"},
                "source_cache_dir": {"type": "string"},
                "runtime_authorized": {"type": "boolean", "default": False},
                "allow_solc_install": {"type": "boolean", "default": False},
                "resume": {"type": "boolean", "default": True},
            },
            "oneOf": [{"required": ["targets"]}, {"required": ["targets_path"]}],
        },
        output_schema=_run_output_schema(),
    )


def _design_resume_contract() -> ToolContract:
    return ToolContract(
        name="vassago_design_resume",
        version="v1",
        description="Resume an existing Vassago design run using the same phase runtime and manifests.",
        aliases=("design_resume", "resume_design"),
        effects=("filesystem_write_artifacts",),
        policy=_base_policy(),
        input_schema={
            "type": "object",
            "required": ["run"],
            "properties": {
                "run": {"type": "string"},
                "dry_run": {"type": "boolean", "default": False},
                "bootstrap_adapters": {"type": "boolean", "default": True},
                "source_fixture": {"type": "string"},
                "source_cache_dir": {"type": "string"},
                "runtime_authorized": {"type": "boolean", "default": False},
                "allow_solc_install": {"type": "boolean", "default": False},
            },
        },
        output_schema=_run_output_schema(),
    )


def _artifact_read_contract() -> ToolContract:
    return ToolContract(
        name="vassago_artifact_read",
        version="v1",
        description="Read one artifact by vassago:// URI from a run directory.",
        aliases=("artifact_read",),
        effects=("filesystem_read_artifact",),
        policy={**_base_policy(), "filesystem_write_artifacts": False},
        input_schema={
            "type": "object",
            "required": ["run", "uri"],
            "properties": {"run": {"type": "string"}, "uri": {"type": "string"}},
        },
        output_schema={
            "type": "object",
            "required": ["status", "run_id", "uri", "artifact_type", "artifact"],
            "properties": {
                "status": {"type": "string"},
                "run_id": {"type": "string"},
                "uri": {"type": "string"},
                "artifact_type": {"type": "string"},
                "artifact": {},
            },
        },
    )


def _run_output_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "required": ["run_dir", "run_id", "status", "executed_count", "skipped_count", "failed_count"],
        "properties": {
            "run_dir": {"type": "string"},
            "run_id": {"type": "string"},
            "status": {"type": "string"},
            "executed_count": {"type": "integer"},
            "skipped_count": {"type": "integer"},
            "failed_count": {"type": "integer"},
            "stop_reason": {"type": ["string", "null"]},
        },
    }
