"""Source resolver interface and bootstrap adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from .target import ContractTargetRef


@dataclass(frozen=True)
class SourceResolution:
    status: str
    provider: str
    target: ContractTargetRef
    abi: list[dict[str, Any]] | None = None
    source_files: dict[str, str] = field(default_factory=dict)
    compiler: dict[str, Any] = field(default_factory=dict)
    proxy_context: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    error: dict[str, Any] | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "provider": self.provider,
            "target": self.target.to_json(),
            "abi": self.abi,
            "source_files": dict(self.source_files),
            "compiler": dict(self.compiler),
            "proxy_context": dict(self.proxy_context),
            "metadata": dict(self.metadata),
            "error": self.error,
        }


class SourceResolver(Protocol):
    def resolve(self, target: ContractTargetRef) -> SourceResolution:
        """Resolve source context for one contract target."""


class NullSourceResolver:
    """Read-only placeholder used before provider adapters exist."""

    def resolve(self, target: ContractTargetRef) -> SourceResolution:
        return SourceResolution(
            status="unresolved",
            provider="null",
            target=target,
            metadata={
                "network": "none",
                "evidence_status": "static_only",
                "note": "No SourceResolver provider configured. This is a skeleton dossier.",
            },
            error={"code": "source_resolver_not_configured", "message": "No provider adapter is configured."},
        )
