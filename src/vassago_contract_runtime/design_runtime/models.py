"""Core models for contract-first design runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from hashlib import sha256
import re
from typing import Any


ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")
CHAIN_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,31}$")
PHASE_ID_RE = re.compile(r"^[0-9]{2}_[a-z0-9_]+$")


class ModelValidationError(ValueError):
    """Validation error with stable machine-readable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message

    def to_json(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}


class PhaseStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class EvidenceStatus(StrEnum):
    STATIC_ONLY = "static_only"
    READ_ONLY_REAL = "read_only_real"
    CANDIDATE = "candidate"
    BLOCKED = "blocked"
    TERMINAL_REJECTED = "terminal_rejected"
    COMPILE_ONLY_PASSED = "compile_only_passed"
    NOT_REPRODUCED = "not_reproduced"
    REPRODUCED_RUNTIME = "reproduced_runtime"
    HUMAN_REVIEW_REQUIRED = "human_review_required"


@dataclass(frozen=True)
class ContractTarget:
    chain: str
    address: str
    label: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    target_id: str = field(init=False)

    def __post_init__(self) -> None:
        chain = self.chain.strip().lower()
        address = self.address.strip().lower()
        if not CHAIN_RE.match(chain):
            raise ModelValidationError("invalid_chain", f"Invalid chain: {self.chain!r}")
        if not ADDRESS_RE.match(address):
            raise ModelValidationError("invalid_address", f"Invalid address: {self.address!r}")
        object.__setattr__(self, "chain", chain)
        object.__setattr__(self, "address", address)
        object.__setattr__(self, "target_id", f"CT-{short_hash(f'{chain}|{address}')}")

    def to_json(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "target_id": self.target_id,
            "chain": self.chain,
            "address": self.address,
            "metadata": dict(self.metadata),
        }
        if self.label:
            payload["label"] = self.label
        return payload

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> "ContractTarget":
        return cls(
            chain=str(payload.get("chain", "")),
            address=str(payload.get("address", "")),
            label=payload.get("label"),
            metadata=dict(payload.get("metadata") or {}),
        )


@dataclass(frozen=True)
class ArtifactSpec:
    name: str
    required: bool = True

    def __post_init__(self) -> None:
        validate_artifact_name(self.name)

    def to_json(self) -> dict[str, Any]:
        return {"name": self.name, "required": self.required}

    @classmethod
    def from_json(cls, payload: dict[str, Any] | str) -> "ArtifactSpec":
        if isinstance(payload, str):
            return cls(name=payload)
        return cls(name=str(payload.get("name", "")), required=bool(payload.get("required", True)))


@dataclass(frozen=True)
class GateSpec:
    gate_id: str
    required_status: str | None = None

    def __post_init__(self) -> None:
        if not self.gate_id or not re.match(r"^[a-z][a-z0-9_]{1,63}$", self.gate_id):
            raise ModelValidationError("invalid_gate_id", f"Invalid gate id: {self.gate_id!r}")

    def to_json(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"gate_id": self.gate_id}
        if self.required_status:
            payload["required_status"] = self.required_status
        return payload

    @classmethod
    def from_json(cls, payload: dict[str, Any] | str | None) -> "GateSpec | None":
        if payload is None:
            return None
        if isinstance(payload, str):
            return cls(gate_id=payload)
        return cls(gate_id=str(payload.get("gate_id") or payload.get("id") or ""), required_status=payload.get("required_status"))


@dataclass(frozen=True)
class PhaseSpec:
    phase_id: str
    name: str
    required: bool = True
    outputs: tuple[ArtifactSpec, ...] = ()
    gate: GateSpec | None = None

    def __post_init__(self) -> None:
        validate_phase_id(self.phase_id)
        if not self.name.strip():
            raise ModelValidationError("invalid_phase_name", "Phase name is required")
        object.__setattr__(self, "outputs", tuple(self.outputs))

    def to_json(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.phase_id,
            "name": self.name,
            "required": self.required,
            "outputs": [item.to_json() for item in self.outputs],
        }
        if self.gate:
            payload["gate"] = self.gate.to_json()
        return payload

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> "PhaseSpec":
        return cls(
            phase_id=str(payload.get("id") or payload.get("phase_id") or ""),
            name=str(payload.get("name") or ""),
            required=bool(payload.get("required", True)),
            outputs=tuple(ArtifactSpec.from_json(item) for item in payload.get("outputs", [])),
            gate=GateSpec.from_json(payload.get("gate")),
        )


@dataclass(frozen=True)
class DesignSpec:
    design_id: str
    version: str
    title: str
    target_model: str
    phases: tuple[PhaseSpec, ...]
    evidence_policy: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not re.match(r"^[a-z0-9][a-z0-9_-]{1,63}$", self.design_id):
            raise ModelValidationError("invalid_design_id", f"Invalid design id: {self.design_id!r}")
        if not self.version.strip():
            raise ModelValidationError("invalid_design_version", "Design version is required")
        if not self.title.strip():
            raise ModelValidationError("invalid_design_title", "Design title is required")
        if not self.phases:
            raise ModelValidationError("missing_phases", "Design must contain at least one phase")
        phase_ids = [phase.phase_id for phase in self.phases]
        if len(set(phase_ids)) != len(phase_ids):
            raise ModelValidationError("duplicate_phase_id", "Design contains duplicate phase ids")
        if phase_ids != sorted(phase_ids):
            raise ModelValidationError("unordered_phases", "Design phases must be sorted by phase id")

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.design_id,
            "version": self.version,
            "title": self.title,
            "target_model": self.target_model,
            "evidence_policy": dict(self.evidence_policy),
            "phases": [phase.to_json() for phase in self.phases],
        }

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> "DesignSpec":
        return cls(
            design_id=str(payload.get("id") or payload.get("design_id") or ""),
            version=str(payload.get("version") or ""),
            title=str(payload.get("title") or ""),
            target_model=str(payload.get("target_model") or "ContractTarget"),
            evidence_policy=dict(payload.get("evidence_policy") or {}),
            phases=tuple(PhaseSpec.from_json(item) for item in payload.get("phases", [])),
        )


@dataclass(frozen=True)
class RunOptions:
    resume: bool = True
    dry_run: bool = False
    continue_optional_failures: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        return {
            "resume": self.resume,
            "dry_run": self.dry_run,
            "continue_optional_failures": self.continue_optional_failures,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_json(cls, payload: dict[str, Any] | None) -> "RunOptions":
        payload = payload or {}
        return cls(
            resume=bool(payload.get("resume", True)),
            dry_run=bool(payload.get("dry_run", False)),
            continue_optional_failures=bool(payload.get("continue_optional_failures", True)),
            metadata=dict(payload.get("metadata") or {}),
        )


def short_hash(value: str, length: int = 12) -> str:
    return sha256(value.encode("utf-8")).hexdigest()[:length]


def validate_phase_id(value: str) -> None:
    if not PHASE_ID_RE.match(value):
        raise ModelValidationError("invalid_phase_id", f"Invalid phase id: {value!r}")


def validate_artifact_name(value: str) -> None:
    if not value or value in {".", ".."}:
        raise ModelValidationError("invalid_artifact_name", f"Invalid artifact name: {value!r}")
    if "/" in value or "\\" in value or "\x00" in value:
        raise ModelValidationError("invalid_artifact_name", f"Artifact name must be local: {value!r}")
