"""Explorer adapter contracts.

The runtime keeps Explorer calls behind this interface so phases can be tested
with fixture/local adapters before any chain API is enabled.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from vassago_contract_runtime.contracts import ContractTargetRef


@dataclass(frozen=True)
class ExplorerContractContext:
    status: str
    provider: str
    target: ContractTargetRef
    abi: list[dict[str, Any]] | None = None
    source_files: dict[str, str] = field(default_factory=dict)
    creation: dict[str, Any] = field(default_factory=dict)
    proxy_context: dict[str, Any] = field(default_factory=dict)
    labels: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    error: dict[str, Any] | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "provider": self.provider,
            "target": self.target.to_json(),
            "abi": self.abi,
            "source_files": dict(self.source_files),
            "creation": dict(self.creation),
            "proxy_context": dict(self.proxy_context),
            "labels": list(self.labels),
            "metadata": dict(self.metadata),
            "error": self.error,
        }


class ExplorerAdapter(Protocol):
    def get_contract_context(self, target: ContractTargetRef) -> ExplorerContractContext:
        """Return read-only Explorer context for one target."""


class NullExplorerAdapter:
    """Offline Explorer adapter used until a provider implementation is wired."""

    def get_contract_context(self, target: ContractTargetRef) -> ExplorerContractContext:
        return ExplorerContractContext(
            status="unresolved",
            provider="null",
            target=target,
            metadata={
                "evidence_status": "static_only",
                "note": "No Explorer adapter configured. No network call was made.",
            },
            error={"code": "explorer_adapter_not_configured", "message": "No Explorer provider is configured."},
        )
