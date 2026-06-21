"""Source resolver interface and bootstrap adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
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


class ExplorerContextAdapter(Protocol):
    def get_contract_context(self, target: ContractTargetRef) -> Any:
        """Return Explorer source context for one contract target."""


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


class FixtureSourceResolver:
    """Local source resolver backed by an explicit JSON fixture.

    This adapter is intentionally filesystem-only. It does not call Explorer,
    RPC, Sourcify, Etherscan or any network provider.
    """

    def __init__(self, records: list[dict[str, Any]], *, provider: str = "fixture") -> None:
        self.provider = provider
        self.records = {_record_key(record): record for record in records}

    @classmethod
    def from_file(cls, path: str | Path) -> "FixtureSourceResolver":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            records = payload.get("targets", [])
        else:
            records = payload
        if not isinstance(records, list):
            raise ValueError("Source fixture must be a list or {'targets': [...]} object.")
        return cls([_as_record(record) for record in records])

    def resolve(self, target: ContractTargetRef) -> SourceResolution:
        record = self.records.get(_target_key(target))
        if record is None:
            return SourceResolution(
                status="unresolved",
                provider=self.provider,
                target=target,
                metadata={
                    "evidence_status": "static_only",
                    "source": "fixture",
                    "note": "No matching local fixture source record was found for this target.",
                },
                error={"code": "fixture_source_not_found", "message": "Target not present in source fixture."},
            )
        return SourceResolution(
            status=str(record.get("status") or "resolved"),
            provider=str(record.get("provider") or self.provider),
            target=target,
            abi=list(record.get("abi") or []),
            source_files=dict(record.get("source_files") or {}),
            compiler=dict(record.get("compiler") or {}),
            proxy_context=dict(record.get("proxy_context") or {}),
            metadata={
                "evidence_status": "static_only",
                "source": "fixture",
                **dict(record.get("metadata") or {}),
            },
            error=record.get("error"),
        )


class ExplorerSourceResolver:
    """Source resolver backed by a read-only Explorer adapter.

    This bridges Explorer contract context into the narrower SourceResolver
    contract used by phase 01. It does not know about Etherscan specifically;
    runtime wiring decides which Explorer adapter and cache to use.
    """

    def __init__(self, explorer: ExplorerContextAdapter) -> None:
        self.explorer = explorer

    def resolve(self, target: ContractTargetRef) -> SourceResolution:
        context = self.explorer.get_contract_context(target)
        context_json = context.to_json() if hasattr(context, "to_json") else dict(context)
        if context_json.get("status") != "resolved":
            return SourceResolution(
                status=str(context_json.get("status") or "unresolved"),
                provider=str(context_json.get("provider") or "explorer"),
                target=target,
                metadata={
                    "evidence_status": "read_only_real",
                    "source": "explorer",
                    **dict(context_json.get("metadata") or {}),
                },
                error=context_json.get("error"),
            )
        compiler_version = str((context_json.get("metadata") or {}).get("compiler_version") or "")
        compiler = {"language": "Solidity", "version": compiler_version} if compiler_version else {}
        return SourceResolution(
            status="resolved",
            provider=str(context_json.get("provider") or "explorer"),
            target=target,
            abi=context_json.get("abi"),
            source_files=dict(context_json.get("source_files") or {}),
            compiler=compiler,
            proxy_context=dict(context_json.get("proxy_context") or {}),
            metadata={
                "evidence_status": "read_only_real",
                "source": "explorer",
                **dict(context_json.get("metadata") or {}),
            },
            error=context_json.get("error"),
        )


def _as_record(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("Each source fixture record must be an object.")
    return value


def _record_key(record: dict[str, Any]) -> str:
    chain = str(record.get("chain") or "").strip().lower()
    address = str(record.get("address") or "").strip().lower()
    if not chain or not address:
        raise ValueError("Each source fixture record requires chain and address.")
    return f"{chain}|{address}"


def _target_key(target: ContractTargetRef) -> str:
    return f"{target.chain.strip().lower()}|{target.address.strip().lower()}"
