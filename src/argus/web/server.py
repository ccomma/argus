from __future__ import annotations

import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse, parse_qs

from argus.analytics import DashboardReporter, ROICalculator
from argus.application import QueryApplication
from argus.assets import CapabilityInventory
from argus.capability_packs import CapabilityPackStore, RolePackStore
from argus.handoff import HandoffManager
from argus.ledger import EventLedger, LearningLedger
from argus.maintenance import MaintenanceEngine, MaintenanceReporter
from argus.paths import ArgusPaths
from argus.playbook import PlaybookRegistry
from argus.security import SecurityScanner
from argus.storage import ContractStorage
from argus.strategy import PolicyEngine, StrategyConfig
from argus.versioning import VersionLock
from argus.web.templates import (
    render_asset_page,
    render_contract_page,
    render_dashboard_page,
    render_learning_page,
    render_maintenance_page,
    render_pack_page,
    render_playbook_page,
    render_role_page,
    render_security_page,
    render_strategy_page,
    render_handoff_page,
)


RouteHandler = Callable[..., Any]


class WebServer:
    def __init__(self, store: str | Path = ".argus", host: str = "127.0.0.1", port: int = 8765) -> None:
        self.store = Path(store)
        self.host = host
        self.port = port
        self._paths = ArgusPaths(self.store)
        self._setup_deps()

    def _setup_deps(self) -> None:
        self.storage = ContractStorage(self._paths.root)
        self.event_ledger = EventLedger(self._paths.root / "ledger" / "events.jsonl")
        self.learning_ledger = LearningLedger(self._paths.root / "ledger" / "candidate_learnings.jsonl")
        self.inventory = CapabilityInventory(self._paths.root / "assets" / "inventory.json")
        self.pack_store = CapabilityPackStore(self._paths.root / "capability-packs")
        self.role_store = RolePackStore(self._paths.root / "role-packs", self.pack_store)
        self.handoff_mgr = HandoffManager(self._paths.root / "handoffs")
        self.query_app = QueryApplication(
            self.storage, self.event_ledger, self.learning_ledger,
            self.inventory, self.pack_store, self.role_store, self.handoff_mgr,
        )
        self.roi = ROICalculator(
            self.storage, self.event_ledger, self.learning_ledger,
            self.inventory, self.pack_store, self.role_store, self.handoff_mgr,
        )
        self.maintenance = MaintenanceEngine(
            self.inventory, self.pack_store, self.role_store, self.storage,
        )
        self.playbook_registry = PlaybookRegistry(self._paths.root / "playbooks")
        self.version_lock = VersionLock.load(self._paths.root / "locks" / "versions.json")
        strategy_path = self._paths.root / "strategy.json"
        self.policy_engine = PolicyEngine.load(strategy_path)
        self.scanner = SecurityScanner()

    def serve(self) -> None:
        server = HTTPServer((self.host, self.port), lambda *a: _Handler(*a, server=self))
        print(f"Argus Workbench: http://{self.host}:{self.port}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            server.shutdown()


class _Handler(BaseHTTPRequestHandler):
    server_ref: WebServer

    def __init__(self, *args: Any, server: WebServer) -> None:
        self.server_ref = server
        super().__init__(*args)

    def log_message(self, format: str, *args: Any) -> None:
        pass

    def _send_json(self, data: Any, status: int = 200) -> None:
        body = json.dumps(data, default=str, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str, status: int = 200) -> None:
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length))

    def do_GET(self) -> None:
        s = self.server_ref
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        qs = parse_qs(parsed.query)

        routes: dict[str, RouteHandler] = {
            "/": lambda: self._send_html(render_dashboard_page(s)),
            "/api/dashboard": lambda: self._send_json(self._dashboard_data(s)),
            "/api/contracts": lambda: self._send_json(self._contracts_data(s)),
            "/api/roles": lambda: self._send_json(self._roles_data(s)),
            "/api/packs": lambda: self._send_json(self._packs_data(s)),
            "/api/assets": lambda: self._send_json(self._assets_data(s)),
            "/api/learnings": lambda: self._send_json(self._learnings_data(s)),
            "/api/maintenance": lambda: self._send_json(self._maintenance_data(s)),
            "/api/strategy": lambda: self._send_json(s.policy_engine.config.to_dict()),
            "/api/playbooks": lambda: self._send_json([p.to_dict() for p in s.playbook_registry.list_all()]),
            "/api/version-locks": lambda: self._send_json(s.version_lock.to_dict()),
            "/api/handoffs": lambda: self._send_json(self._handoffs_data(s)),
            "/contracts": lambda: self._send_html(render_contract_page(s)),
            "/roles": lambda: self._send_html(render_role_page(s)),
            "/packs": lambda: self._send_html(render_pack_page(s)),
            "/assets": lambda: self._send_html(render_asset_page(s)),
            "/learnings": lambda: self._send_html(render_learning_page(s)),
            "/maintenance": lambda: self._send_html(render_maintenance_page(s)),
            "/strategy": lambda: self._send_html(render_strategy_page(s)),
            "/playbooks": lambda: self._send_html(render_playbook_page(s)),
            "/security": lambda: self._send_html(render_security_page(s)),
            "/handoffs": lambda: self._send_html(render_handoff_page(s)),
        }

        # API detail routes
        if path.startswith("/api/contracts/"):
            contract_id = path.split("/api/contracts/")[1]
            result = s.query_app.query_contracts(contract_id=contract_id)
            self._send_json(result)
            return
        if path.startswith("/api/roles/"):
            role_id = path.split("/api/roles/")[1]
            result = s.query_app.query_roles(role_id=role_id)
            self._send_json(result)
            return
        if path.startswith("/api/assets/"):
            asset_id = path.split("/api/assets/")[1]
            result = s.query_app.query_assets(asset_id=asset_id)
            self._send_json(result)
            return

        handler = routes.get(path)
        if handler:
            handler()
        else:
            self._send_json({"error": "not found"}, 404)

    def do_POST(self) -> None:
        s = self.server_ref
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        body = self._read_body()

        if path == "/api/strategy":
            config = StrategyConfig.from_dict(body)
            s.policy_engine = PolicyEngine(config)
            strategy_path = s._paths.root / "strategy.json"
            s.policy_engine.save(strategy_path)
            self._send_json({"status": "ok"})
            return

        if path == "/api/playbooks":
            from argus.playbook import Playbook
            pb = Playbook.create(**body)
            s.playbook_registry.save(pb)
            self._send_json(pb.to_dict(), 201)
            return

        if path == "/api/version-locks":
            entry = s.version_lock.lock(
                asset_id=body.get("asset_id", ""),
                asset_type=body.get("asset_type", ""),
                source=body.get("source", ""),
                version=body.get("version", ""),
                reason=body.get("reason", ""),
            )
            s.version_lock.save()
            self._send_json(entry.to_dict(), 201)
            return

        if path == "/api/security/scan":
            content = body.get("content", "")
            source = body.get("source", "")
            location = body.get("location", "")
            report = s.scanner.scan_capability(content, source, location)
            self._send_json(report.to_dict())
            return

        self._send_json({"error": "not found"}, 404)

    def do_DELETE(self) -> None:
        s = self.server_ref
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path.startswith("/api/playbooks/"):
            playbook_id = path.split("/api/playbooks/")[1]
            ok = s.playbook_registry.delete(playbook_id)
            self._send_json({"deleted": ok})
            return

        if path.startswith("/api/version-locks/"):
            asset_id = path.split("/api/version-locks/")[1]
            ok = s.version_lock.unlock(asset_id)
            s.version_lock.save()
            self._send_json({"deleted": ok})
            return

        self._send_json({"error": "not found"}, 404)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    # ---- data helpers ----

    def _dashboard_data(self, s: WebServer) -> dict:
        d = DashboardReporter(s._paths.root / "reports").write(s.roi)
        return {
            "contract_roi": d.contract_roi.to_dict(),
            "learning_roi": d.learning_roi.to_dict(),
            "role_roi": d.role_roi.to_dict(),
        }

    def _contracts_data(self, s: WebServer) -> dict:
        contracts = s.storage.list_contracts()
        return {"contracts": [c.to_dict() for c in contracts], "total": len(contracts)}

    def _roles_data(self, s: WebServer) -> dict:
        roles = s.role_store.list_latest()
        return {"roles": [r.to_dict() for r in roles], "total": len(roles)}

    def _packs_data(self, s: WebServer) -> dict:
        packs = s.pack_store.list_latest()
        return {"packs": [p.to_dict() for p in packs], "total": len(packs)}

    def _assets_data(self, s: WebServer) -> dict:
        assets = s.inventory.list_assets()
        return {"assets": [a.to_dict() for a in assets], "total": len(assets)}

    def _learnings_data(self, s: WebServer) -> dict:
        learnings = s.learning_ledger.list_learnings()
        return {"learnings": [lrn.to_dict() for lrn in learnings], "total": len(learnings)}

    def _maintenance_data(self, s: WebServer) -> dict:
        report = s.maintenance.run()
        return report.to_dict()

    def _handoffs_data(self, s: WebServer) -> dict:
        handoffs = s.handoff_mgr.list_all()
        return {"handoffs": [h.to_dict() for h in handoffs], "total": len(handoffs)}
