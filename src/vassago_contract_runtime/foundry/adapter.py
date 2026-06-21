"""Foundry adapter contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class FoundryHarnessInput:
    target_id: str
    harness_name: str
    source_files: dict[str, str]
    test_files: dict[str, str]
    foundry_toml: str | None = None
    fork: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "harness_name": self.harness_name,
            "source_file_count": len(self.source_files),
            "test_file_count": len(self.test_files),
            "has_foundry_toml": self.foundry_toml is not None,
            "fork": dict(self.fork),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class FoundryRunResult:
    status: str
    provider: str
    target_id: str
    command: list[str] = field(default_factory=list)
    stdout: str = ""
    stderr: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    error: dict[str, Any] | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "provider": self.provider,
            "target_id": self.target_id,
            "command": list(self.command),
            "stdout": self.stdout[-4000:],
            "stderr": self.stderr[-4000:],
            "metadata": dict(self.metadata),
            "error": self.error,
        }


class FoundryAdapter(Protocol):
    def compile_harness(self, item: FoundryHarnessInput) -> FoundryRunResult:
        """Compile a harness without runtime execution."""

    def run_local_fork(self, item: FoundryHarnessInput) -> FoundryRunResult:
        """Run local/fork tests only when runtime gate is satisfied."""


class NullFoundryAdapter:
    def compile_harness(self, item: FoundryHarnessInput) -> FoundryRunResult:
        return FoundryRunResult(
            status="unavailable",
            provider="null",
            target_id=item.target_id,
            metadata={"evidence_status": "static_only", "note": "No Foundry adapter configured."},
            error={"code": "foundry_adapter_not_configured", "message": "No Foundry adapter is configured."},
        )

    def run_local_fork(self, item: FoundryHarnessInput) -> FoundryRunResult:
        return FoundryRunResult(
            status="blocked",
            provider="null",
            target_id=item.target_id,
            metadata={
                "evidence_status": "static_only",
                "note": "Runtime execution requires an explicit Foundry adapter and runtime-ready gate.",
            },
            error={"code": "foundry_runtime_not_configured", "message": "No Foundry runtime adapter is configured."},
        )
