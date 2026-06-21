"""Contract target reference helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from vassago_contract_runtime.design_runtime.models import ContractTarget


@dataclass(frozen=True)
class ContractTargetRef:
    target_id: str
    chain: str
    address: str
    label: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_target(cls, target: ContractTarget) -> "ContractTargetRef":
        return cls(
            target_id=target.target_id,
            chain=target.chain,
            address=target.address,
            label=target.label,
            metadata=dict(target.metadata),
        )

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
