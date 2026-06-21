"""Slither adapter contract.

Slither is intentionally hidden behind this interface so the design runtime can
fall back cleanly when compilation context is incomplete or Slither is not
installed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class SlitherInput:
    target_id: str
    source_files: dict[str, str]
    compile_context: dict[str, Any] = field(default_factory=dict)
    target_contract: str | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "source_file_count": len(self.source_files),
            "compile_context": dict(self.compile_context),
            "target_contract": self.target_contract,
        }


@dataclass(frozen=True)
class SlitherAnalysisResult:
    status: str
    provider: str
    target_id: str
    detectors: list[dict[str, Any]] = field(default_factory=list)
    ir: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    error: dict[str, Any] | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "provider": self.provider,
            "target_id": self.target_id,
            "detectors": list(self.detectors),
            "ir": dict(self.ir),
            "metadata": dict(self.metadata),
            "error": self.error,
        }


class SlitherAdapter(Protocol):
    def analyze(self, item: SlitherInput) -> SlitherAnalysisResult:
        """Analyze a source bundle and return detector/IR context."""


class NullSlitherAdapter:
    def analyze(self, item: SlitherInput) -> SlitherAnalysisResult:
        return SlitherAnalysisResult(
            status="unavailable",
            provider="null",
            target_id=item.target_id,
            metadata={
                "evidence_status": "static_only",
                "note": "No Slither adapter configured. No compiler or Slither process was run.",
            },
            error={"code": "slither_adapter_not_configured", "message": "No Slither adapter is configured."},
        )
