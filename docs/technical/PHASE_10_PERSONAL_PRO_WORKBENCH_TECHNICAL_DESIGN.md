# Phase 10: Personal Pro Workbench Technical Design

> Context loading: 新会话默认先读 `docs/context/CURRENT_HANDOFF.md`，再按需读取本技术设计。本文件回答模块、接口、数据和风险边界，不记录每日执行状态。

## 1. Overview

Phase 10 将 Argus 从纯 CLI 工具升级为个人专业工作台，新增五大模块：(1) 本地 Web 工作台提供 11 页可视化界面；(2) 策略引擎实现风险分级自动化治理；(3) Playbook 注册中心管理可复用任务流程模板；(4) 版本锁定机制保证能力资产确定性；(5) 安全扫描器检测提示注入和供应链风险。

## 2. Architecture

```
web/                        strategy/                  playbook/
  WebServer                   PolicyEngine               Playbook (frozen)
    └─ _Handler               ├─ StrategyConfig            PlaybookRegistry
      ├─ 11 HTML 页面         │  ├─ PolicyRule[]          │  ├─ save/load
      ├─ REST API (12+ 端点)  │  ├─ trusted_sources       │  ├─ list_all
      └─ 动态路由 (3 资源)    │  ├─ blocked_sources       │  └─ delete
                              │  └─ auto_install_scopes
versioning/                  security/
  VersionLock                  SecurityScanner
    ├─ LockEntry[]             ├─ PROMPT_INJECTION_PATTERNS
    ├─ lock/unlock/get         ├─ SUPPLY_CHAIN_RISK_PATTERNS
    └─ save/load               └─ scan_capability → ScanReport
```

WebServer 聚合所有 Phase 1-10 依赖（storage、ledger、inventory、pack_store、role_store、handoff_mgr、roi、maintenance、playbook_registry、version_lock、policy_engine、scanner），初始化为单例并通过 `_Handler.server_ref` 注入到每个 HTTP 请求处理器。

## 3. Data Model

```text
# ---- Strategy ----
RiskLevel (enum): LOW="low", MEDIUM="medium", HIGH="high"
ActionDecision (enum): AUTO="auto", ASK="ask", BLOCK="block"

PolicyRule (frozen dataclass)
- action_type: str                 # 操作类型标识
- risk_level: RiskLevel            # 风险等级
- decision: ActionDecision         # 决策结果
- description: str                 # 规则说明
- conditions: dict[str, Any]       # 匹配条件

StrategyConfig (mutable dataclass)
- rules: list[PolicyRule]          # 规则列表，默认 11 条
- trusted_sources: list[str]       # 信任来源
- blocked_sources: list[str]       # 阻止来源
- auto_install_scopes: list[str]   # 允许自动安装的作用域
- require_confirmation_for: list[str] # 需确认的操作类型

# ---- Playbook ----
Playbook (frozen dataclass)
- playbook_id: str                 # SHA-1 前 12 位
- name: str
- description: str
- question_strategies: list[str]   # 提问策略
- confirmation_points: list[str]   # 确认点
- deliverable_templates: list[dict] # 交付物模板
- contract_templates: list[dict]   # 合约模板
- roles: list[str]                 # 所需角色
- capability_pack_ids: list[str]   # 所需能力包
- tags: list[str]
- version: int                     # 默认 1
- created_at: int / updated_at: int

# ---- Version Lock ----
LockEntry (frozen dataclass)
- asset_id: str                    # 资产唯一 ID
- asset_type: str                  # 资产类型
- source: str                      # 来源
- version: str                     # 锁定版本
- locked_at: int                   # Unixtime
- reason: str                      # 锁定原因

VersionLock (mutable dataclass)
- entries: list[LockEntry]         # 同 asset_id 原地更新
- lockfile_path: Path | None       # 持久化路径绑定

# ---- Security ----
SecurityFinding (frozen dataclass)
- severity: str                    # high / low
- category: str                    # prompt_injection / supply_chain / external_source
- description: str
- location: str
- evidence: str

ScanReport (mutable dataclass)
- target: str                      # 扫描目标标识
- findings: list[SecurityFinding]
- risk_score: float                # min(1.0, len(findings) * 0.15)
- passed: bool                     # 无 high 严重度发现则为 True
```

## 4. Interfaces

### Web 工作台

```text
GET  /
GET  /contracts   /roles   /packs   /assets
GET  /learnings   /maintenance      /strategy
GET  /playbooks   /security         /handoffs

GET  /api/dashboard   /api/contracts   /api/roles   /api/packs
GET  /api/assets      /api/learnings   /api/maintenance
GET  /api/strategy    /api/playbooks   /api/version-locks
GET  /api/handoffs    /api/contracts/<id>  /api/roles/<id>  /api/assets/<id>

POST /api/strategy       # 保存策略配置 { rules, ... }
POST /api/playbooks      # 创建 playbook { name, description, ... }
POST /api/version-locks  # 锁定版本 { asset_id, asset_type, source, version, reason }
POST /api/security/scan  # 安全扫描 { content, source, location }

DELETE /api/playbooks/<id>      # 删除 playbook
DELETE /api/version-locks/<id>  # 解除版本锁定

OPTIONS 对所有路径返回 CORS 预检头
```

WebServer 初始化：`WebServer(store=".argus", host="127.0.0.1", port=8765).serve()`

### CLI

```text
argus web                                    # 启动 Web 工作台
  --store <.argus> --host 127.0.0.1 --port 8765

argus strategy show|set-rule|reset
  --store <.argus>
  set-rule: --action-type --risk-level --decision [--description]

argus playbook create|list|show|delete
  create: --name [--description --role --tag]
  show/delete: <playbook_id>

argus version-lock lock|unlock|list
  lock: --asset-id --asset-type --source --version [--reason]
  unlock: --asset-id

argus security scan
  --content <text> | --file <path> [--source]

argus workbench <sub> ...  (组合命令入口，覆盖 strategy/playbook/version-lock/security/web/team/onboarding/lifecycle/registry/feedback)
```

### Python API

```python
from argus.web import WebServer
from argus.strategy import PolicyEngine, PolicyRule, RiskLevel, ActionDecision, StrategyConfig
from argus.playbook import Playbook, PlaybookRegistry
from argus.versioning import LockEntry, VersionLock
from argus.security import SecurityScanner

# 策略引擎
engine = PolicyEngine.load(path)                                    # 加载或默认配置
decision = engine.evaluate("install_external_executable", RiskLevel.HIGH)
is_trusted = engine.is_trusted_source("https://skills.example.com")
engine.save(path)

# Playbook
pb = Playbook.create(name="my-workflow", description="...", roles=["developer"])
registry = PlaybookRegistry(dir); registry.save(pb); registry.list_all()

# 版本锁定
lock = VersionLock.load(path)
entry = lock.lock(asset_id="my-skill", asset_type="skill", source="...", version="2.1")
lock.unlock("my-skill"); lock.save()

# 安全扫描
scanner = SecurityScanner()
report = scanner.scan_capability(content="...text...", source="https://...", location="cli")
# report.passed, report.risk_score, report.findings
```

## 5. Storage

| 模块 | 存储路径 | 格式 |
|------|---------|------|
| 策略配置 | `<store>/strategy.json` | JSON |
| Playbook | `<store>/playbooks/{playbook_id}.json` | JSON (每本一本) |
| 版本锁 | `<store>/locks/versions.json` | JSON (集中锁文件) |
| Web 模板 | 代码内联（`web/templates.py`） | Python 字符串 |

WebServer 不将报表持久化到自身目录，而是委托 DashboardReporter 和 MaintenanceReporter 写入 Phase 9 的 `reports/` 和 `maintenance/` 目录。安全扫描为纯内存操作，不持久化结果。

## 6. Governance and Security

- **策略引擎安全**：PolicyEngine.evaluate() 对未匹配规则的操作采用保守策略（默认 ASK）。高风险未知 MCP 来源默认 BLOCK。阻止名单优先于信任名单（blocklist-first 安全检查）。
- **CORS 安全**：Web 工作台开放 CORS `*` 为本地开发便利，生产部署时应通过反向代理限制。
- **安全扫描模式**：13 条提示注入模式（`ignore previous instructions`、`<system>` 等）和 10 条供应链风险模式（`eval(`、`| bash`、`rm -rf /`、`chmod 777` 等）。外部 URL 来源能力标记为 `external_source` 低风险发现。风险评分线性累加，上限 1.0，存在任何 `high` 发现时 `passed = False`。
- **版本锁定安全**：同一 `asset_id` 再次锁定原地替换旧条目，保证唯一性。需手动调用 save() 持久化，避免中途崩溃丢失整批变更。

## 7. Failure Modes

- **策略文件缺失**：PolicyEngine.load() 返回默认安全配置（11 条规则），不会因文件丢失而崩溃。
- **版本锁文件缺失**：VersionLock.load() 返回空列表并绑定路径，后续 save() 自动创建目录。
- **安全扫描空内容**：空字符串扫描产生空 findings 列表，risk_score = 0.0，passed = True。
- **Playbook 查询不存在**：registry.load(nonexistent_id) 返回 None，CLI 返回错误 JSON。
- **Web 端口冲突**：HTTPServer 抛出 OSError，由调用方处理（当前 CLI 直接传播异常）。
- **策略配置 JSON 格式错误**：json.loads() 异常直接传播，调用方应捕获并提示用户修复或重置。

## 8. Test Strategy

- **Unit Tests**：PolicyEngine.evaluate() 命中/未命中/风险回退路径。SecurityScanner 各扫描方法的已知模式匹配。Playbook.create() 的 ID 生成和字段默认值。VersionLock.lock() 重复锁定的原地替换行为。
- **Integration Tests**：HTTP 请求路由匹配、GET/POST/DELETE 端点响应格式、JSON 序列化完整性。CLI 子命令端到端（策略设置→文件持久化→重新加载→输出一致）。
- **Acceptance Tests**：启动 WebServer 后 curl 各页面检查 200 状态码和 HTML 关键元素。安全扫描已知注入文本返回正确的 findings 和 passed 判定。

## 9. Compatibility

- **Phase 1-9 组件无 breaking change**：WebServer 聚合所有前序服务实例，不修改原有接口。
- **模板无外部文件依赖**：所有 HTML/CSS 内联在 `web/templates.py` 中，不引入前端构建工具或 CDN。
- **策略配置格式稳定**：StrategyConfig.to_dict/from_dict 缺失字段使用默认值，向后兼容旧策略文件。
- **版本锁文件格式**：含 `entries` 数组，每个条目字段有默认值兜底。

## 10. Open Questions

- Web 工作台是否需要身份认证层（当前无认证，仅监听 127.0.0.1），后续团队场景可能需要 token/OAuth。
- 策略规则的 `conditions` 匹配语义（当前 `context is None` 时宽松匹配所有同类型操作），是否需要更严格的安全默认值（None 时也阻止）。
- 安全扫描模式列表是否需要支持外部配置文件加载，以适应用户自定义威胁模式。
- 11 页 HTML 模板是否需要抽象为 Jinja2 等模板引擎（当前为纯 Python f-string 拼接，符合零依赖约束）。
