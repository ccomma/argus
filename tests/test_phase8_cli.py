import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from argus.assets import CapabilityAsset, CapabilityInventory
from argus.capability_packs import CapabilityPackStore, RolePackStore
from argus.capability_packs.creation import CapabilityPackCreator
from argus.contracts import ContractSession, QuestionStrategy, WorkContractBuilder
from argus.storage import ContractStorage


class Phase8CLITest(unittest.TestCase):
    def test_contract_list_shows_stored_contracts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / ".argus"
            storage = ContractStorage(store)
            session = ContractSession(intent="test contract for list", strategy=QuestionStrategy.standard())
            contract = WorkContractBuilder().build(session)
            storage.save_contract(contract)

            out = subprocess.run(
                [sys.executable, "-m", "argus.cli", "contract", "list", "--store", str(store)],
                check=True, capture_output=True, text=True,
            )
            contracts = json.loads(out.stdout)
            self.assertEqual(len(contracts), 1)
            self.assertEqual(contracts[0]["intent"], "test contract for list")

    def test_contract_list_empty_when_no_contracts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / ".argus"
            out = subprocess.run(
                [sys.executable, "-m", "argus.cli", "contract", "list", "--store", str(store)],
                check=True, capture_output=True, text=True,
            )
            self.assertEqual(json.loads(out.stdout), [])

    def test_packs_list_shows_stored_packs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / ".argus"
            pack_store = CapabilityPackStore(Path(store) / "capability-packs")
            creator = CapabilityPackCreator(store=pack_store)
            manifest = creator.create(
                pack_id="test-pack",
                display_name="Test Pack",
                description="A test capability pack",
                required_asset_ids=[],
                optional_asset_ids=[],
                assets=[],
                created_by="test",
            ).manifest
            pack_store.write(manifest)

            out = subprocess.run(
                [sys.executable, "-m", "argus.cli", "packs", "list", "--store", str(store)],
                check=True, capture_output=True, text=True,
            )
            packs = json.loads(out.stdout)
            self.assertEqual(len(packs), 1)
            self.assertEqual(packs[0]["pack_id"], "test-pack")

    def test_roles_list_shows_stored_roles(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / ".argus"
            pack_store = CapabilityPackStore(Path(store) / "capability-packs")
            role_store = RolePackStore(Path(store) / "role-packs", pack_store)
            role_store.create(
                role_id="test-role",
                display_name="Test Role",
                required_pack_ids=[],
                optional_pack_ids=[],
                created_by="test",
            )

            out = subprocess.run(
                [sys.executable, "-m", "argus.cli", "roles", "list", "--store", str(store)],
                check=True, capture_output=True, text=True,
            )
            roles = json.loads(out.stdout)
            self.assertEqual(len(roles), 1)
            self.assertEqual(roles[0]["role_id"], "test-role")

    def test_query_contract_returns_contract_with_handoffs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / ".argus"
            storage = ContractStorage(store)
            session = ContractSession(intent="query test contract", strategy=QuestionStrategy.standard())
            contract = WorkContractBuilder().build(session)
            storage.save_contract(contract)

            out = subprocess.run(
                [sys.executable, "-m", "argus.cli", "query", "contract", contract.id, "--store", str(store)],
                check=True, capture_output=True, text=True,
            )
            results = json.loads(out.stdout)
            self.assertTrue(isinstance(results, list))
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["id"], contract.id)

    def test_query_role_returns_role_with_cross_references(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / ".argus"
            pack_store = CapabilityPackStore(Path(store) / "capability-packs")
            role_store = RolePackStore(Path(store) / "role-packs", pack_store)
            role = role_store.create(
                role_id="query-test-role",
                display_name="Query Test Role",
                required_pack_ids=[],
                optional_pack_ids=[],
                created_by="test",
            )

            out = subprocess.run(
                [sys.executable, "-m", "argus.cli", "query", "role", "query-test-role", "--store", str(store)],
                check=True, capture_output=True, text=True,
            )
            results = json.loads(out.stdout)
            self.assertTrue(isinstance(results, list))
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["role_id"], "query-test-role")

    def test_mcp_serve_accepts_initialize(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            proc = subprocess.Popen(
                [sys.executable, "-m", "argus.cli", "mcp-serve", "--store", str(Path(tmpdir) / ".argus")],
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
            finally:
                proc.terminate()
                proc.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
