"""Web 工作台 HTML 模板 - 定义 CSS 主题（暗色 GitHub 风格）和 11 个页面渲染函数。"""

from __future__ import annotations

import json

# 暗色主题 CSS，模仿 GitHub Dark 风格，统一视觉语言
CSS = """
:root {
  --bg: #0d1117; --fg: #c9d1d9; --border: #30363d;
  --accent: #58a6ff; --green: #3fb950; --red: #f85149;
  --orange: #d2991d; --muted: #8b949e; --card: #161b22;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
  background: var(--bg); color: var(--fg); line-height: 1.5; }
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
header { border-bottom: 1px solid var(--border); padding: 12px 24px;
  background: var(--card); display: flex; align-items: center; gap: 20px; }
header h1 { font-size: 18px; font-weight: 600; }
nav { display: flex; gap: 4px; flex-wrap: wrap; }
nav a { padding: 6px 12px; border-radius: 6px; font-size: 13px; color: var(--muted); }
nav a:hover, nav a.active { background: var(--border); color: var(--fg); text-decoration: none; }
main { max-width: 1200px; margin: 0 auto; padding: 24px; }
h2 { font-size: 20px; margin-bottom: 16px; }
.card { background: var(--card); border: 1px solid var(--border); border-radius: 8px;
  padding: 20px; margin-bottom: 16px; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
.stat { font-size: 28px; font-weight: 700; }
.stat-label { font-size: 12px; color: var(--muted); text-transform: uppercase; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px;
  font-weight: 500; }
.badge-green { background: #1b3826; color: var(--green); }
.badge-red { background: #3d1f1f; color: var(--red); }
.badge-orange { background: #3d3520; color: var(--orange); }
.badge-muted { background: var(--border); color: var(--muted); }
table { width: 100%; border-collapse: collapse; }
th, td { text-align: left; padding: 10px 12px; border-bottom: 1px solid var(--border); font-size: 13px; }
th { color: var(--muted); font-weight: 600; font-size: 12px; text-transform: uppercase; }
tr:hover { background: rgba(255,255,255,0.02); }
pre { background: #0d1117; padding: 16px; border-radius: 8px; overflow-x: auto;
  font-size: 12px; border: 1px solid var(--border); }
button, .btn { display: inline-block; padding: 6px 14px; border-radius: 6px; border: 1px solid var(--border);
  background: var(--card); color: var(--fg); cursor: pointer; font-size: 13px; }
button:hover { background: var(--border); }
.btn-primary { background: #1f6feb; border-color: #1f6feb; color: #fff; }
.btn-primary:hover { background: #388bfd; }
input, textarea, select { background: #0d1117; border: 1px solid var(--border); border-radius: 6px;
  padding: 8px 12px; color: var(--fg); font-size: 13px; width: 100%; }
textarea { min-height: 100px; resize: vertical; }
.form-group { margin-bottom: 12px; }
.form-group label { display: block; font-size: 12px; color: var(--muted); margin-bottom: 4px;
  font-weight: 600; text-transform: uppercase; }
"""


def _page(title: str, content: str, active_nav: str = "") -> str:
    """组装完整 HTML 页面，含导航栏、CSS 和内联内容。

    1. 构建 11 项导航链接列表
    2. 高亮当前活跃页（active CSS class）
    3. 拼接完整的 HTML5 结构返回
    """
    nav_items = [
        ("/", "Dashboard"),
        ("/contracts", "Contracts"),
        ("/roles", "Roles"),
        ("/packs", "Packs"),
        ("/assets", "Assets"),
        ("/learnings", "Learnings"),
        ("/maintenance", "Maintenance"),
        ("/strategy", "Strategy"),
        ("/playbooks", "Playbooks"),
        ("/handoffs", "Handoffs"),
        ("/security", "Security"),
    ]
    nav_html = "\n".join(
        f'<a href="{url}" class="{"active" if url == active_nav else ""}">{label}</a>'
        for url, label in nav_items
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} - Argus Workbench</title>
<style>{CSS}</style></head>
<body>
<header><h1>Argus Workbench</h1><nav>{nav_html}</nav></header>
<main>{content}</main>
</body></html>"""


def _json_block(data) -> str:
    """将数据格式化为带缩进的 JSON 代码块，用 <pre> 标签包裹。"""
    return f"<pre>{json.dumps(data, indent=2, default=str)}</pre>"


def render_dashboard_page(s: "WebServer") -> str:
    """渲染 Dashboard 首页：左侧显合约/学习/角色/Handoff 统计卡片，下方显 ROI 详情。"""
    from argus.analytics import DashboardReporter
    d = DashboardReporter(s._paths.root / "reports").write(s.roi)
    cr = d.contract_roi
    lr = d.learning_roi
    rr = d.role_roi

    content = f"""
<h2>Dashboard</h2>
<div class="grid">
  <div class="card"><div class="stat-label">Total Contracts</div><div class="stat">{cr.total_contracts}</div></div>
  <div class="card"><div class="stat-label">Avg Completeness</div><div class="stat">{cr.avg_completeness:.1%}</div></div>
  <div class="card"><div class="stat-label">Total Learnings</div><div class="stat">{lr.total_learnings}</div></div>
  <div class="card"><div class="stat-label">Promoted Learnings</div><div class="stat">{lr.promoted_count}</div></div>
  <div class="card"><div class="stat-label">Total Roles</div><div class="stat">{rr.total_roles}</div></div>
  <div class="card"><div class="stat-label">Total Handoffs</div><div class="stat">{rr.total_handoffs}</div></div>
</div>

<h2 style="margin-top:28px;">Contract ROI</h2>
<div class="card">
  <p><strong>By Status:</strong> {_json_block(cr.by_status)}</p>
  <p><strong>Avg Question Rounds:</strong> {cr.avg_question_rounds}</p>
  <p><strong>Deliverable Pass Rate:</strong> {cr.deliverable_pass_rate:.1%}</p>
</div>

<h2>Learning ROI</h2>
<div class="card">
  <p><strong>By Type:</strong> {_json_block(lr.by_type)}</p>
  <p><strong>By Scope:</strong> {_json_block(lr.by_scope)}</p>
  <p><strong>Avg Confidence:</strong> {lr.avg_confidence:.2f}</p>
</div>

<h2>Role ROI</h2>
<div class="card">
  <p><strong>Total Roles:</strong> {rr.total_roles}</p>
  <p><strong>Roles in Handoffs:</strong> {len(rr.roles_used_in_handoffs)}</p>
  <p><strong>Avg Packs per Role:</strong> {rr.avg_packs_per_role:.1f}</p>
</div>
"""
    return _page("Dashboard", content, "/")


def render_contract_page(s: "WebServer") -> str:
    """渲染合约列表页：展示所有工作合约的 ID、意图摘要、状态和 JSON 链接。"""
    contracts = s.storage.list_contracts()
    rows = ""
    for c in contracts:
        status_cls = "badge-green" if c.status == "done" else ("badge-orange" if c.status == "executing" else "badge-muted")
        rows += f"""<tr>
<td><code>{c.contract_id}</code></td>
<td>{c.intent[:60]}{"..." if len(c.intent) > 60 else ""}</td>
<td><span class="badge {status_cls}">{c.status}</span></td>
<td><a href="/api/contracts/{c.contract_id}">[json]</a></td>
</tr>"""

    content = f"""<h2>Work Contracts</h2>
<div class="card"><p>{len(contracts)} contracts</p></div>
<table><thead><tr><th>ID</th><th>Intent</th><th>Status</th><th></th></tr></thead>
<tbody>{rows}</tbody></table>"""
    return _page("Contracts", content, "/contracts")


def render_role_page(s: "WebServer") -> str:
    """渲染角色页：列出所有角色包，显示角色 ID 和名称。"""
    roles = s.role_store.list_latest()
    rows = ""
    for r in roles:
        rows += f"""<tr>
<td><code>{r.role_id}</code></td>
<td>{r.name}</td>
<td><a href="/api/roles/{r.role_id}">[json]</a></td>
</tr>"""

    content = f"""<h2>Role Packs</h2>
<div class="card"><p>{len(roles)} roles</p></div>
<table><thead><tr><th>ID</th><th>Name</th><th></th></tr></thead>
<tbody>{rows}</tbody></table>"""
    return _page("Roles", content, "/roles")


def render_pack_page(s: "WebServer") -> str:
    """渲染能力包页：列出所有能力包，显示包 ID 和版本。"""
    packs = s.pack_store.list_latest()
    rows = ""
    for p in packs:
        rows += f"""<tr>
<td><code>{p.pack_id}</code></td>
<td>v{p.version}</td>
<td><a href="/api/packs">[json]</a></td>
</tr>"""

    content = f"""<h2>Capability Packs</h2>
<div class="card"><p>{len(packs)} packs</p></div>
<table><thead><tr><th>ID</th><th>Version</th><th></th></tr></thead>
<tbody>{rows}</tbody></table>"""
    return _page("Packs", content, "/packs")


def render_asset_page(s: "WebServer") -> str:
    """渲染资产页：列出所有能力资产，含名称、类型、状态标签和 JSON 链接。"""
    assets = s.inventory.list_assets()
    rows = ""
    for a in assets:
        status_cls = "badge-green" if a.status == "active" else ("badge-red" if a.status == "deprecated" else "badge-muted")
        rows += f"""<tr>
<td><code>{a.id}</code></td><td>{a.name}</td><td>{a.type}</td>
<td><span class="badge {status_cls}">{a.status}</span></td>
<td><a href="/api/assets/{a.id}">[json]</a></td>
</tr>"""

    content = f"""<h2>Capability Assets</h2>
<div class="card"><p>{len(assets)} assets</p></div>
<table><thead><tr><th>ID</th><th>Name</th><th>Type</th><th>Status</th><th></th></tr></thead>
<tbody>{rows}</tbody></table>"""
    return _page("Assets", content, "/assets")


def render_learning_page(s: "WebServer") -> str:
    """渲染学习页：列出候选人学习条目，含摘要、类型和状态标签。"""
    learnings = s.learning_ledger.list_learnings()
    rows = ""
    for lrn in learnings:
        status_cls = "badge-green" if lrn.status == "promoted" else ("badge-orange" if lrn.status == "pending" else "badge-muted")
        rows += f"""<tr>
<td><code>{lrn.id}</code></td>
<td>{lrn.summary[:60]}{"..." if len(lrn.summary) > 60 else ""}</td>
<td>{lrn.type}</td>
<td><span class="badge {status_cls}">{lrn.status}</span></td>
</tr>"""

    content = f"""<h2>Candidate Learnings</h2>
<div class="card"><p>{len(learnings)} learnings</p></div>
<table><thead><tr><th>ID</th><th>Summary</th><th>Type</th><th>Status</th></tr></thead>
<tbody>{rows}</tbody></table>"""
    return _page("Learnings", content, "/learnings")


def render_maintenance_page(s: "WebServer") -> str:
    """渲染维护页：显示维护摘要卡片（重复数、冲突、废弃项等）和完整 JSON 报告。"""
    report = s.maintenance.run()
    content = f"""<h2>Maintenance Report</h2>
<div class="grid">
  <div class="card"><div class="stat-label">Total Assets</div><div class="stat">{report.summary.get("total_assets", 0)}</div></div>
  <div class="card"><div class="stat-label">Duplicates</div><div class="stat">{report.summary.get("duplicates", 0)}</div></div>
  <div class="card"><div class="stat-label">Conflicts</div><div class="stat">{report.summary.get("conflicts", 0)}</div></div>
  <div class="card"><div class="stat-label">Deprecated</div><div class="stat">{report.summary.get("deprecated", 0)}</div></div>
  <div class="card"><div class="stat-label">Unused Packs</div><div class="stat">{report.summary.get("unused_packs", 0)}</div></div>
  <div class="card"><div class="stat-label">Unused Roles</div><div class="stat">{report.summary.get("unused_roles", 0)}</div></div>
</div>
<div class="card"><h3>Full Report</h3>{_json_block(report.to_dict())}</div>"""
    return _page("Maintenance", content, "/maintenance")


def render_strategy_page(s: "WebServer") -> str:
    """渲染策略页：以表格展示所有策略规则（动作、风险等级、决策、描述），附原始配置 JSON。"""
    config = s.policy_engine.config
    rules_html = ""
    for i, r in enumerate(config.rules):
        rules_html += f"""<tr>
<td>{r.action_type}</td>
<td><span class="badge badge-{"green" if r.risk_level.value == "low" else ("orange" if r.risk_level.value == "medium" else "red")}">{r.risk_level.value}</span></td>
<td><span class="badge badge-{"green" if r.decision.value == "auto" else ("orange" if r.decision.value == "ask" else "red")}">{r.decision.value}</span></td>
<td>{r.description}</td>
</tr>"""

    content = f"""<h2>Strategy Configuration</h2>
<div class="card"><h3>Policy Rules</h3>
<table><thead><tr><th>Action</th><th>Risk</th><th>Decision</th><th>Description</th></tr></thead>
<tbody>{rules_html}</tbody></table></div>
<div class="card"><h3>Raw Config</h3>{_json_block(config.to_dict())}</div>"""
    return _page("Strategy", content, "/strategy")


def render_playbook_page(s: "WebServer") -> str:
    """渲染 Playbook 页：列出所有个人 playbook，含名称、描述、版本和角色数。"""
    playbooks = s.playbook_registry.list_all()
    rows = ""
    for pb in playbooks:
        rows += f"""<tr>
<td><code>{pb.playbook_id}</code></td><td>{pb.name}</td>
<td>{pb.description[:50]}{"..." if len(pb.description) > 50 else ""}</td>
<td>v{pb.version}</td><td>{len(pb.roles)} roles</td>
</tr>"""

    content = f"""<h2>Personal Playbook Registry</h2>
<div class="card"><p>{len(playbooks)} playbooks</p></div>
<table><thead><tr><th>ID</th><th>Name</th><th>Description</th><th>Version</th><th>Roles</th></tr></thead>
<tbody>{rows}</tbody></table>"""
    return _page("Playbooks", content, "/playbooks")


def render_security_page(s: "WebServer") -> str:
    """渲染安全扫描页：提供一个表单用于粘贴能力内容进行安全扫描，结果通过 JS fetch 异步展示。"""
    content = f"""<h2>Security Scanner</h2>
<div class="card">
<h3>Scan Capability Content</h3>
<form method="post" action="/api/security/scan" onsubmit="event.preventDefault(); scanContent();">
<div class="form-group"><label>Content to scan</label>
<textarea id="scan-content" placeholder="Paste skill, rule, or prompt content to scan..."></textarea></div>
<div class="form-group"><label>Source URL (optional)</label>
<input id="scan-source" placeholder="https://..."></div>
<button type="submit" class="btn-primary">Scan</button>
</form>
<div id="scan-results" style="margin-top:16px;"></div>
</div>
<script>
async function scanContent() {{
  const content = document.getElementById('scan-content').value;
  const source = document.getElementById('scan-source').value;
  const resp = await fetch('/api/security/scan', {{
    method: 'POST', headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify({{content, source, location: 'web-ui'}})
  }});
  const data = await resp.json();
  document.getElementById('scan-results').innerHTML =
    '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
}}
</script>"""
    return _page("Security", content, "/security")


def render_handoff_page(s: "WebServer") -> str:
    """渲染 Handoff 页：列出角色交接记录，含来源角色、目标角色、关联合约和原因。"""
    handoffs = s.handoff_mgr.list_all()
    rows = ""
    for h in handoffs:
        rows += f"""<tr>
<td><code>{h.id}</code></td><td>{h.from_role_id}</td><td>{h.to_role_id}</td>
<td><code>{h.contract_id}</code></td><td>{h.handoff_reason[:40]}</td>
</tr>"""

    content = f"""<h2>Role Handoffs</h2>
<div class="card"><p>{len(handoffs)} handoffs</p></div>
<table><thead><tr><th>ID</th><th>From</th><th>To</th><th>Contract</th><th>Reason</th></tr></thead>
<tbody>{rows}</tbody></table>"""
    return _page("Handoffs", content, "/handoffs")
