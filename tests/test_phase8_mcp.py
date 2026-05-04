import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from argus.assets import CapabilityAsset, CapabilityInventory
from argus.contracts import ContractSession, QuestionStrategy, WorkContractBuilder
from argus.storage import ContractStorage
from argus.mcp.server import MCPServer


class Phase8MCPTest(unittest.TestCase):
    def _make_server(self, tmpdir: str) -> MCPServer:
        return MCPServer(store=Path(tmpdir) / ".argus")

    def test_initialize_handshake_returns_protocol_version_and_capabilities(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            server = self._make_server(tmpdir)
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test-client", "version": "1.0"},
                },
            }
            response = server._handle(request)
            self.assertIsNotNone(response)
            self.assertIn("result", response)
            self.assertEqual(response["result"]["protocolVersion"], "2024-11-05")
            self.assertIn("tools", response["result"]["capabilities"])

    def test_initialized_notification_returns_none(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            server = self._make_server(tmpdir)
            response = server._handle({"jsonrpc": "2.0", "method": "notifications/initialized"})
            self.assertIsNone(response)

    def test_tools_list_returns_all_registered_tools(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            server = self._make_server(tmpdir)
            response = server._handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
            self.assertIn("result", response)
            tools = response["result"]["tools"]
            tool_names = {t["name"] for t in tools}
            expected = {
                "query_contracts", "query_roles", "query_packs",
                "query_learnings", "query_assets", "check_role",
                "run_resolution", "handoff_role", "submit_event", "list_handoffs",
            }
            self.assertTrue(expected.issubset(tool_names))

    def test_tools_call_unknown_tool_returns_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            server = self._make_server(tmpdir)
            response = server._handle({
                "jsonrpc": "2.0", "id": 3, "method": "tools/call",
                "params": {"name": "nonexistent_tool", "arguments": {}},
            })
            self.assertIn("error", response)
            self.assertEqual(response["error"]["code"], -32601)

    def test_query_contracts_tool_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            server = self._make_server(tmpdir)
            response = server._handle({
                "jsonrpc": "2.0", "id": 4, "method": "tools/call",
                "params": {"name": "query_contracts", "arguments": {}},
            })
            result = response["result"]["content"][0]["text"]
            data = json.loads(result)
            self.assertEqual(data["total"], 0)

    def test_query_roles_tool_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            server = self._make_server(tmpdir)
            response = server._handle({
                "jsonrpc": "2.0", "id": 5, "method": "tools/call",
                "params": {"name": "query_roles", "arguments": {}},
            })
            result = response["result"]["content"][0]["text"]
            data = json.loads(result)
            self.assertEqual(data["total"], 0)

    def test_submit_event_and_query_learnings(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            server = self._make_server(tmpdir)
            submit = server._handle({
                "jsonrpc": "2.0", "id": 6, "method": "tools/call",
                "params": {"name": "submit_event", "arguments": {
                    "source": "test", "agent": "claude",
                    "event_type": "user_correction",
                    "evidence": {"message": "corrected"},
                }},
            })
            result = json.loads(submit["result"]["content"][0]["text"])
            self.assertIn("event_id", result)

            query = server._handle({
                "jsonrpc": "2.0", "id": 7, "method": "tools/call",
                "params": {"name": "query_learnings", "arguments": {"type": "correction"}},
            })
            data = json.loads(query["result"]["content"][0]["text"])
            # Learnings may be empty since extract hasn't run, but events exist
            self.assertIn("total", data)

    def test_handoff_role_tool_creates_record(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            server = self._make_server(tmpdir)
            response = server._handle({
                "jsonrpc": "2.0", "id": 8, "method": "tools/call",
                "params": {"name": "handoff_role", "arguments": {
                    "from_role_id": "researcher",
                    "to_role_id": "product-manager",
                    "contract_id": "c1",
                    "handoff_reason": "research phase complete",
                }},
            })
            result = json.loads(response["result"]["content"][0]["text"])
            self.assertEqual(result["from_role_id"], "researcher")
            self.assertEqual(result["to_role_id"], "product-manager")
            self.assertIn("id", result)

            # Verify via list_handoffs
            list_resp = server._handle({
                "jsonrpc": "2.0", "id": 9, "method": "tools/call",
                "params": {"name": "list_handoffs", "arguments": {"contract_id": "c1"}},
            })
            list_data = json.loads(list_resp["result"]["content"][0]["text"])
            self.assertEqual(list_data["total"], 1)

    def test_unknown_method_returns_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            server = self._make_server(tmpdir)
            response = server._handle({"jsonrpc": "2.0", "id": 10, "method": "unknown/method"})
            self.assertIn("error", response)
            self.assertEqual(response["error"]["code"], -32601)

    def test_mcp_server_cli_startup(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / ".argus"
            proc = subprocess.Popen(
                [sys.executable, "-m", "argus.mcp", "--store", str(store)],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True,
            )
            try:
                init_request = json.dumps({
                    "jsonrpc": "2.0", "id": 1, "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "test", "version": "1.0"},
                    },
                }) + "\n"
                stdout, stderr = proc.communicate(input=init_request, timeout=5)
                response = json.loads(stdout.strip())
                self.assertIn("result", response)
                self.assertEqual(response["result"]["serverInfo"]["name"], "argus-mcp")
            finally:
                proc.terminate()
                proc.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
