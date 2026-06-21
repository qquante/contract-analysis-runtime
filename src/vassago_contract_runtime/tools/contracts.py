"""Agent-facing tool contracts and invocation result models."""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
from typing import Any, Callable


ToolHandler = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class ToolContract:
    name: str
    version: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    effects: tuple[str, ...] = ()
    policy: dict[str, Any] = field(default_factory=dict)
    aliases: tuple[str, ...] = ()

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "effects": list(self.effects),
            "policy": dict(self.policy),
            "aliases": list(self.aliases),
        }


@dataclass(frozen=True)
class ToolInvocation:
    tool_name: str
    inputs: dict[str, Any]
    agent_id: str = "local"
    invocation_id: str = field(init=False)

    def __post_init__(self) -> None:
        seed = json.dumps({"tool": self.tool_name, "agent": self.agent_id, "inputs": self.inputs}, sort_keys=True)
        object.__setattr__(self, "invocation_id", f"TI-{sha256(seed.encode('utf-8')).hexdigest()[:12]}")


@dataclass(frozen=True)
class ToolRunResult:
    status: str
    invocation_id: str
    tool_name: str
    output: dict[str, Any] = field(default_factory=dict)
    error: dict[str, Any] | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "invocation_id": self.invocation_id,
            "tool_name": self.tool_name,
            "output": dict(self.output),
            "error": self.error,
        }


@dataclass(frozen=True)
class RegisteredTool:
    contract: ToolContract
    handler: ToolHandler


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}
        self._aliases: dict[str, str] = {}

    def register(self, contract: ToolContract, handler: ToolHandler) -> None:
        if contract.name in self._tools or contract.name in self._aliases:
            raise ValueError(f"Duplicate tool name: {contract.name}")
        self._tools[contract.name] = RegisteredTool(contract=contract, handler=handler)
        for alias in contract.aliases:
            if alias in self._tools or alias in self._aliases:
                raise ValueError(f"Duplicate tool alias: {alias}")
            self._aliases[alias] = contract.name

    def resolve(self, name: str) -> RegisteredTool:
        canonical = self._aliases.get(name, name)
        if canonical not in self._tools:
            raise ValueError(f"Unknown tool: {name}")
        return self._tools[canonical]

    def list_contracts(self) -> list[dict[str, Any]]:
        return [tool.contract.to_json() for tool in self._tools.values()]

    def describe(self, name: str) -> dict[str, Any]:
        return self.resolve(name).contract.to_json()

    def invoke(self, invocation: ToolInvocation) -> ToolRunResult:
        try:
            tool = self.resolve(invocation.tool_name)
            output = tool.handler(invocation.inputs)
            return ToolRunResult(
                status="completed",
                invocation_id=invocation.invocation_id,
                tool_name=tool.contract.name,
                output=output,
            )
        except Exception as exc:
            return ToolRunResult(
                status="failed",
                invocation_id=invocation.invocation_id,
                tool_name=invocation.tool_name,
                error={"code": exc.__class__.__name__, "message": str(exc)},
            )
