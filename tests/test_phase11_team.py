import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from argus.team import MemberRole, Permission, Team, TeamCatalog, TeamCatalogManager, TeamMember, TeamPolicy


class Phase11TeamModelTest(unittest.TestCase):
    def test_team_create(self):
        team = Team.create("t1", "Test Team", "A test team")
        self.assertEqual(team.team_id, "t1")
        self.assertEqual(team.name, "Test Team")
        self.assertEqual(len(team.members), 0)

    def test_team_add_member(self):
        team = Team.create("t1", "Test Team")
        member = TeamMember(member_id="u1", name="Alice", role=MemberRole.ADMIN)
        team.add_member(member)
        self.assertEqual(len(team.members), 1)
        self.assertTrue(team.get_member("u1").has_permission(Permission.WRITE))

    def test_team_add_duplicate_member_updates(self):
        team = Team.create("t1", "Test Team")
        m1 = TeamMember(member_id="u1", name="Alice", role=MemberRole.MEMBER)
        m2 = TeamMember(member_id="u1", name="Alice", role=MemberRole.ADMIN)
        team.add_member(m1)
        team.add_member(m2)
        self.assertEqual(len(team.members), 1)
        self.assertEqual(team.get_member("u1").role, MemberRole.ADMIN)

    def test_team_remove_member(self):
        team = Team.create("t1", "Test Team")
        team.add_member(TeamMember(member_id="u1", name="Alice"))
        self.assertTrue(team.remove_member("u1"))
        self.assertIsNone(team.get_member("u1"))
        self.assertFalse(team.remove_member("u1"))

    def test_team_roundtrip(self):
        team = Team.create("t1", "Test Team")
        team.add_member(TeamMember(member_id="u1", name="Alice", role=MemberRole.OWNER))
        data = team.to_dict()
        restored = Team.from_dict(data)
        self.assertEqual(restored.team_id, team.team_id)
        self.assertEqual(len(restored.members), 1)

    def test_member_permissions(self):
        owner = TeamMember(member_id="u1", name="Owner", role=MemberRole.OWNER)
        viewer = TeamMember(member_id="u2", name="Viewer", role=MemberRole.VIEWER)
        self.assertTrue(owner.has_permission(Permission.DELETE))
        self.assertTrue(owner.has_permission(Permission.ADMIN))
        self.assertTrue(viewer.has_permission(Permission.READ))
        self.assertFalse(viewer.has_permission(Permission.WRITE))

    def test_team_save_and_load_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "t1.json"
            team = Team.create("t1", "Test Team")
            team.add_member(TeamMember(member_id="u1", name="Alice"))
            path.write_text(json.dumps(team.to_dict(), indent=2), encoding="utf-8")
            restored = Team.from_dict(json.loads(path.read_text(encoding="utf-8")))
            self.assertEqual(restored.name, "Test Team")
            self.assertEqual(len(restored.members), 1)


class Phase11TeamCatalogTest(unittest.TestCase):
    def test_catalog_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "t1.json"
            cat = TeamCatalog(team_id="t1")
            cat.add_contract("c1")
            cat.add_role("r1")
            cat.add_pack("p1")
            cat.save(path)
            self.assertTrue(path.exists())
            loaded = TeamCatalog.load(path)
            self.assertEqual(loaded.team_id, "t1")
            self.assertIn("c1", loaded.contract_ids)

    def test_catalog_add_template(self):
        cat = TeamCatalog(team_id="t1")
        cat.add_template("prd", {"sections": ["goal", "context"]})
        cat.add_template("prd", {"sections": ["goal", "context", "risks"]})
        self.assertEqual(len(cat.shared_templates), 1)
        self.assertEqual(len(cat.shared_templates[0]["content"]["sections"]), 3)

    def test_catalog_manager_list_all(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = TeamCatalogManager(Path(tmpdir))
            mgr.save(TeamCatalog(team_id="t1"))
            mgr.save(TeamCatalog(team_id="t2"))
            all_cats = mgr.list_all()
            self.assertEqual(len(all_cats), 2)


class Phase11TeamPolicyTest(unittest.TestCase):
    def test_policy_defaults(self):
        policy = TeamPolicy(team_id="t1")
        self.assertTrue(policy.require_approval_for_install)
        self.assertTrue(policy.shared_contract_templates)
        self.assertFalse(policy.auto_install_trusted)

    def test_policy_can_install(self):
        policy = TeamPolicy(
            team_id="t1",
            blocked_sources=["evil.com"],
            allowed_sources=["github.com/trusted"],
        )
        self.assertFalse(policy.can_install("evil.com", MemberRole.OWNER))
        self.assertTrue(policy.can_install("github.com/trusted", MemberRole.MEMBER))
        self.assertTrue(policy.can_install("unknown.com", MemberRole.ADMIN))

    def test_policy_can_share(self):
        policy = TeamPolicy(team_id="t1")
        self.assertTrue(policy.can_share_contract(MemberRole.ADMIN))
        self.assertTrue(policy.can_share_contract(MemberRole.MEMBER))
        self.assertFalse(policy.can_share_contract(MemberRole.VIEWER))

    def test_policy_exceptions(self):
        policy = TeamPolicy(team_id="t1")
        policy.add_exception("github.com/tool", "install", "approved tool")
        self.assertEqual(len(policy.exception_rules), 1)
        self.assertTrue(policy.remove_exception("github.com/tool", "install"))
        self.assertEqual(len(policy.exception_rules), 0)

    def test_policy_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "t1.json"
            policy = TeamPolicy(team_id="t1", auto_install_trusted=True)
            policy.save(path)
            self.assertTrue(path.exists())
            loaded = TeamPolicy.load(path)
            self.assertTrue(loaded.auto_install_trusted)


class Phase11OnboardingTest(unittest.TestCase):
    def test_onboarding_pack_render(self):
        from argus.onboarding import OnboardingPack
        pack = OnboardingPack(
            pack_id="test-pack",
            repo_name="test-repo",
            team_id="t1",
            rules=["Use pytest for testing", "Run lint before commit"],
            required_capabilities=["skill/python-testing", "mcp/github"],
            recommended_packs=["pack-dev"],
            roles=["architect", "implementer"],
            setup_instructions=["git clone test-repo", "pip install -e ."],
            created_at=1700000000,
        )
        md = pack.render_markdown()
        self.assertIn("test-repo", md)
        self.assertIn("pytest for testing", md)
        self.assertIn("skill/python-testing", md)

    def test_onboarding_generator_empty(self):
        from argus.onboarding import OnboardingGenerator
        from argus.assets import CapabilityInventory
        from argus.capability_packs import CapabilityPackStore, RolePackStore
        from argus.storage import ContractStorage

        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir)
            storage = ContractStorage(store)
            inventory = CapabilityInventory(store / "assets" / "inventory.json")
            pack_store = CapabilityPackStore(store / "capability-packs")
            role_store = RolePackStore(store / "role-packs", pack_store)
            gen = OnboardingGenerator(storage, inventory, pack_store, role_store)
            pack = gen.generate("my-repo")
            self.assertEqual(pack.repo_name, "my-repo")
            self.assertTrue(pack.pack_id)

    def test_onboarding_generator_save(self):
        from argus.onboarding import OnboardingGenerator
        from argus.assets import CapabilityInventory
        from argus.capability_packs import CapabilityPackStore, RolePackStore
        from argus.storage import ContractStorage

        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir)
            storage = ContractStorage(store)
            inventory = CapabilityInventory(store / "assets" / "inventory.json")
            pack_store = CapabilityPackStore(store / "capability-packs")
            role_store = RolePackStore(store / "role-packs", pack_store)
            gen = OnboardingGenerator(storage, inventory, pack_store, role_store)
            pack = gen.generate("my-repo")
            out_dir = store / "onboarding"
            md_path = gen.save(pack, out_dir)
            self.assertTrue(md_path.exists())
            self.assertTrue((out_dir / f"{pack.pack_id}.json").exists())


class Phase11TeamCLITest(unittest.TestCase):
    def test_team_create_and_list_cli(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / ".argus"
            subprocess.run(
                [sys.executable, "-m", "argus.cli", "team", "create",
                 "--store", str(store), "--team-id", "cli-team", "--name", "CLI Team"],
                check=True, capture_output=True, text=True,
            )
            out = subprocess.run(
                [sys.executable, "-m", "argus.cli", "team", "list", "--store", str(store)],
                check=True, capture_output=True, text=True,
            )
            data = json.loads(out.stdout)
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["name"], "CLI Team")

    def test_team_add_and_remove_member_cli(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / ".argus"
            subprocess.run(
                [sys.executable, "-m", "argus.cli", "team", "create",
                 "--store", str(store), "--team-id", "t1", "--name", "T1"],
                check=True, capture_output=True, text=True,
            )
            subprocess.run(
                [sys.executable, "-m", "argus.cli", "team", "add-member",
                 "--store", str(store), "--team-id", "t1", "--member-id", "u1",
                 "--name", "Alice", "--role", "admin"],
                check=True, capture_output=True, text=True,
            )
            out = subprocess.run(
                [sys.executable, "-m", "argus.cli", "team", "show", "--store", str(store), "--team-id", "t1"],
                check=True, capture_output=True, text=True,
            )
            data = json.loads(out.stdout)
            self.assertEqual(len(data["members"]), 1)

            subprocess.run(
                [sys.executable, "-m", "argus.cli", "team", "remove-member",
                 "--store", str(store), "--team-id", "t1", "--member-id", "u1"],
                check=True, capture_output=True, text=True,
            )
            out2 = subprocess.run(
                [sys.executable, "-m", "argus.cli", "team", "show", "--store", str(store), "--team-id", "t1"],
                check=True, capture_output=True, text=True,
            )
            data2 = json.loads(out2.stdout)
            self.assertEqual(len(data2["members"]), 0)

    def test_team_policy_cli(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / ".argus"
            subprocess.run(
                [sys.executable, "-m", "argus.cli", "team", "create",
                 "--store", str(store), "--team-id", "t1", "--name", "T1"],
                check=True, capture_output=True, text=True,
            )
            out = subprocess.run(
                [sys.executable, "-m", "argus.cli", "team", "policy",
                 "--store", str(store), "--team-id", "t1"],
                check=True, capture_output=True, text=True,
            )
            data = json.loads(out.stdout)
            self.assertEqual(data["team_id"], "t1")

    def test_onboarding_generate_cli(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / ".argus"
            out = subprocess.run(
                [sys.executable, "-m", "argus.cli", "onboarding", "generate",
                 "--store", str(store), "--repo-name", "test-repo"],
                check=True, capture_output=True, text=True,
            )
            data = json.loads(out.stdout)
            self.assertIn("markdown_path", data)
            self.assertIn("pack", data)
            self.assertEqual(data["pack"]["repo_name"], "test-repo")


if __name__ == "__main__":
    unittest.main()
