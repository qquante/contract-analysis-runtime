"""Minimal local MCP stdio server for the design runtime tools."""

from __future__ import annotations

import json
import sys
from typing import Any, TextIO

from vassago_contract_runtime.tools import ToolInvocation, ToolRegistry, build_runtime_tool_registry


PROTOCOL_VERSION = "2025-11-25"
SERVER_INFO = {
    "name": "vassago-contract-runtime",
    "title": "Vassago Contract Runtime",
    "version": "0.1.0",
}


class McpServer:
    """JSON-RPC MCP server exposing only campaign-level tools."""

    def __init__(self, registry: ToolRegistry | None = None) -> None:
        self.registry = registry or build_runtime_tool_registry()
        self.initialized = False

    def handle_message(self, message: dict[str, Any]) -> dict[str, Any] | None:
        request_id = message.get("id")
        method = message.get("method")
        if message.get("jsonrpc") != "2.0" or not isinstance(method, str):
            return _error(request_id, -32600, "Invalid request")
        if method == "initialize":
            return _result(request_id, self._initialize(message.get("params") or {}))
        if method == "notifications/initialized":
            self.initialized = True
            return None
        if method == "ping":
            return _result(request_id, {})
        if method == "tools/list":
            return _result(request_id, {"tools": [self._mcp_tool(item) for item in self.registry.list_contracts()]})
        if method == "tools/call":
            return self._call_tool(request_id, message.get("params") or {})
        if request_id is None:
            return None
        return _error(request_id, -32601, f"Method not found: {method}")

    def _initialize(self, params: dict[str, Any]) -> dict[str, Any]:
        requested_version = str(params.get("protocolVersion") or PROTOCOL_VERSION)
        return {
            "protocolVersion": requested_version,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": SERVER_INFO,
            "instructions": (
                "Use vassago_design_run, vassago_design_resume and vassago_artifact_read only. "
                "This server is local-only, no-shell and no-broadcast."
            ),
        }

    def _mcp_tool(self, contract: dict[str, Any]) -> dict[str, Any]:
        return {
            "name": contract["name"],
            "title": contract["name"],
            "description": _tool_description(contract),
            "inputSchema": contract["input_schema"],
            "outputSchema": contract["output_schema"],
            "annotations": {
                "readOnlyHint": contract["name"] == "vassago_artifact_read",
                "destructiveHint": False,
                "openWorldHint": False,
            },
        }

    def _call_tool(self, request_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("name")
        if not isinstance(name, str):
            return _error(request_id, -32602, "tools/call requires params.name")
        arguments = params.get("arguments") or {}
        if not isinstance(arguments, dict):
            return _error(request_id, -32602, "tools/call requires object params.arguments")
        try:
            self.registry.resolve(name)
        except ValueError as exc:
            return _error(request_id, -32602, str(exc))
        result = self.registry.invoke(ToolInvocation(name, arguments, agent_id="mcp-stdio"))
        payload = result.to_json()
        is_error = result.status != "completed"
        return _result(
            request_id,
            {
                "content": [{"type": "text", "text": json.dumps(payload, sort_keys=True)}],
                "structuredContent": payload,
                "isError": is_error,
            },
        )


def run_stdio(
    *,
    input_stream: TextIO | None = None,
    output_stream: TextIO | None = None,
    server: McpServer | None = None,
) -> int:
    input_stream = input_stream or sys.stdin
    output_stream = output_stream or sys.stdout
    server = server or McpServer()
    for raw_line in input_stream:
        line = raw_line.strip()
        if not line:
            continue
        response = _handle_line(server, line)
        if response is None:
            continue
        output_stream.write(json.dumps(response, separators=(",", ":")) + "\n")
        output_stream.flush()
    return 0


def _handle_line(server: McpServer, line: str) -> dict[str, Any] | None:
    try:
        message = json.loads(line)
    except json.JSONDecodeError as exc:
        return _error(None, -32700, "Parse error", {"message": str(exc)})
    if not isinstance(message, dict):
        return _error(None, -32600, "Invalid request")
    try:
        return server.handle_message(message)
    except Exception as exc:
        request_id = message.get("id")
        return _error(request_id, -32603, "Internal error", {"message": str(exc)})


def _tool_description(contract: dict[str, Any]) -> str:
    policy = contract.get("policy") or {}
    return (
        f"{contract['description']} "
        f"Policy: local_only={bool(policy.get('local_only'))}, "
        f"no_shell={bool(policy.get('no_shell'))}, "
        f"no_broadcast={bool(policy.get('no_broadcast'))}."
    )


def _result(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id: Any, code: int, message: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code, "message": message}
    if data:
        payload["data"] = data
    return {"jsonrpc": "2.0", "id": request_id, "error": payload}
