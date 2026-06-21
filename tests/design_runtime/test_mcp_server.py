from __future__ import annotations

from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest

from vassago_contract_runtime.mcp import McpServer, run_stdio


TARGET = {"chain": "eth", "address": "0x1111111111111111111111111111111111111111"}


class McpServerTests(unittest.TestCase):
    def test_initialize_declares_tools_capability(self) -> None:
        response = McpServer().handle_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "test"}},
            }
        )

        self.assertEqual(response["result"]["protocolVersion"], "2025-11-25")
        self.assertIn("tools", response["result"]["capabilities"])
        self.assertEqual(response["result"]["serverInfo"]["name"], "vassago-contract-runtime")

    def test_tools_list_exposes_only_campaign_level_tools(self) -> None:
        response = McpServer().handle_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})

        tools = response["result"]["tools"]
        names = {item["name"] for item in tools}
        self.assertEqual(names, {"vassago_design_run", "vassago_design_resume", "vassago_artifact_read"})
        for item in tools:
            self.assertIn("inputSchema", item)
            self.assertNotIn("shell", item["name"])
            self.assertEqual(item["annotations"]["destructiveHint"], False)

    def test_tools_call_runs_design_and_returns_structured_content(self) -> None:
        server = McpServer()
        with tempfile.TemporaryDirectory() as tmp:
            response = server.handle_message(
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": "vassago_design_run",
                        "arguments": {
                            "design": "sc01-access",
                            "targets": [TARGET],
                            "output": str(Path(tmp) / "run"),
                            "bootstrap_adapters": True,
                            "source_fixture": "tests/fixtures/source_fixture.json",
                        },
                    },
                }
            )

            result = response["result"]
            self.assertEqual(result["isError"], False)
            self.assertEqual(result["structuredContent"]["status"], "completed")
            self.assertEqual(result["structuredContent"]["output"]["failed_count"], 0)
            self.assertEqual(result["content"][0]["type"], "text")

    def test_unknown_tool_returns_protocol_error(self) -> None:
        response = McpServer().handle_message(
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {"name": "vassago_shell", "arguments": {}},
            }
        )

        self.assertEqual(response["error"]["code"], -32602)
        self.assertIn("Unknown tool", response["error"]["message"])

    def test_stdio_loop_writes_only_json_rpc_responses(self) -> None:
        request = json.dumps({"jsonrpc": "2.0", "id": 5, "method": "tools/list"}) + "\n"
        output = StringIO()

        code = run_stdio(input_stream=StringIO(request), output_stream=output)

        self.assertEqual(code, 0)
        lines = [line for line in output.getvalue().splitlines() if line]
        self.assertEqual(len(lines), 1)
        response = json.loads(lines[0])
        self.assertEqual(response["id"], 5)
        self.assertIn("tools", response["result"])

    def test_initialized_notification_has_no_response(self) -> None:
        output = StringIO()

        run_stdio(
            input_stream=StringIO('{"jsonrpc":"2.0","method":"notifications/initialized"}\n'),
            output_stream=output,
        )

        self.assertEqual(output.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
