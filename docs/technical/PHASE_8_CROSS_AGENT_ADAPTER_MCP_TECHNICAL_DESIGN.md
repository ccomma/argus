# Phase 8: Cross-Agent Adapter & MCP Server Technical Design

> Context loading: 新会话默认先读 `docs/context/CURRENT_HANDOFF.md`，再按需读取本技术设计。本文件回答模块、接口、数据和风险边界，不记录每日执行状态。

## 1. Overview

Phase 8 实现三个核心能力：(1) 跨 Agent 适配器层，将 Codex/Claude 转录数据标准化为 Argus EventRecord；(2) 基于 JSON-RPC 2.0 over stdio 的 MCP 服务器，通过 10 个工具对外暴露 Argus 的查询和操作能力；(3) 角色交接记录系统，管理 Agent 角色间的上下文移交。QueryApplication 作为统一查询门面，支撑 CLI 和 MCP 双重消费。

## 2. Architecture

```
外部 Agent 转录                 Argus 内部                   外部消费
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Codex 转录文件 ──→ CodexAdapter ──┐
                    (TranscriptIngestor)
                                  ├──→ EventLedger ──→ .argus/ledger/events.json
Claude JSONL ────→ ClaudeAdapter ─┘

┌─────────────────────────────────────────────────────────────────┐
│                        QueryApplication                         │
│  query_contracts / query_roles / query_packs / query_learnings  │
│  query_assets / check_role / run_resolution / submit_event      │
│  handoff_role / list_handoffs / list_events                     │
└──────────────┬────────────────────────────────────┬─────────────┘
               │                                    │
        CLI 命令 (query)                    MCP Server (stdio JSON-RPC)
        argus query contract <id>           ┌──────────────────────────┐
        argus query role <id>               │ MCPServer.serve()        │
                                                                       │  10 tools:                  │
HandoffManager ──→ .argus/handoffs/         │ query_contracts/roles/    │
  HandoffRecord   {id}.json                 │ packs/learnings/assets    │
                                            │ check_role/run_resolution │
  BaseAdapter (ABC)                         │ handoff_role/submit_event │
    ├─ CodexAdapter                         │ list_handoffs             │
    └─ ClaudeAdapter                        └──────────────────────────┘
```

核心模块：
- `src/argus/adapter/base.py` — `BaseAdapter` ABC
- `src/argus/adapter/codex.py` — `CodexAdapter`
- `src/argus/adapter/claude.py` — `ClaudeAdapter`
- `src/argus/mcp/server.py` — `MCPServer`，10 工具 JSON-RPC
- `src/argus/mcp/__main__.py` — `python -m argus.mcp` 入口
- `src/argus/handoff/models.py` — `HandoffRecord`
- `src/argus/handoff/manager.py` — `HandoffManager`
- `src/argus/application/query.py` — `QueryApplication`

## 3. Data Model

### 3.1 适配器模型

```text
BaseAdapter (ABC)
  - agent_name: str (abstract property) — 返回 "codex" 或 "claude"
  - normalize_event(self, raw: dict) -> EventRecord (abstract) — 标准化原始记录
  - submit_event(self, event: EventRecord) -> str — 提交事件，返回 event.id

CodexAdapter(BaseAdapter)
  - agent_name → "codex"
  - 持有 TranscriptIngestor 用于批量导入转录文件
  - normalize_event: 字段映射 raw["session"], raw["event_type"], raw["evidence"]
  - submit_event: 写入 self._ledger

ClaudeAdapter(BaseAdapter)
  - agent_name → "claude"
  - normalize_event: 处理 Claude 特有命名差异（type→event_type, message→evidence, session_id→session）
  - ingest_transcript(path): 逐行 JSONL 解析，批量写入账本
  - submit_event: 写入 self._ledger
```

### 3.2 MCP 服务器模型

```text
MCPServer
  - _paths: ArgusPaths — 从 --store 解析所有存储路径
  - _query_app: QueryApplication — 门面
  - _tools: dict[str, tuple[str, str, ToolFn]] — 工具注册表 (描述, 详细说明, 处理函数)
  - serve() — 启动 stdio 事件循环，阻塞直至输入流关闭
  - _handle(request) — 分发 JSON-RPC method: initialize / notifications/initialized / tools/list / tools/call

MCP 协议：JSON-RPC 2.0 over stdio
  - method="initialize" → 返回 protocolVersion, capabilities, serverInfo
  - method="tools/list" → 返回工具名/描述/inputSchema 列表
  - method="tools/call" → 委托给对应 ToolFn 执行
  - 错误码：-32601 (unknown method/tool), -32603 (execution error)
```

### 3.3 交接记录模型

```text
HandoffRecord (frozen dataclass)
  - id: str                     # handoff-<sha1_16>，内容寻址
  - from_role_id: str           # 来源角色 ID
  - to_role_id: str             # 目标角色 ID
  - contract_id: str            # 关联合约 ID
  - context: dict[str, Any]     # 交接上下文数据
  - created_at: int             # Unix 时间戳（秒）
  - handoff_reason: str         # 交接原因
  工厂方法: HandoffRecord.create(*, from_role_id, to_role_id, contract_id, context, handoff_reason)
```

### 3.4 查询门面模型

```text
QueryApplication
  - storage: ContractStorage
  - event_ledger: EventLedger
  - learning_ledger: LearningLedger
  - inventory: CapabilityInventory
  - pack_store: CapabilityPackStore
  - role_store: RolePackStore
  - handoff_mgr: HandoffManager
  - _resolver: CapabilityResolver
  - _resolution_reporter: ResolutionReporter | None
```

## 4. Interfaces

### 4.1 Adapter Python API

```python
# CodexAdapter
adapter = CodexAdapter(ledger=EventLedger(path))
adapter.normalize_event({"session": "s1", "event_type": "tool_call", "evidence": {...}})
adapter.submit_event(event)  # → event.id
adapter.ingest_transcript("/path/to/transcript.json")  # → count

# ClaudeAdapter
adapter = ClaudeAdapter(ledger=EventLedger(path))
adapter.normalize_event({"type": "tool_use", "session_id": "s1", "message": {...}})
adapter.ingest_transcript("/path/to/claude_transcript.jsonl")  # → count
```

### 4.2 MCP 服务器

启动方式：
```bash
python -m argus.mcp --store .argus          # 模块入口
argus mcp-serve --store .argus              # CLI 入口
```

10 个 MCP 工具：

| 工具名 | 参数 | 功能 |
|--------|------|------|
| `query_contracts` | status, role_id, contract_id, workspace | 查询合约，附加 handoffs |
| `query_roles` | role_id | 查询角色，附加 handoffs |
| `query_packs` | pack_id | 查询能力包 |
| `query_learnings` | contract_id, type, scope, min_confidence | 查询学习项 |
| `query_assets` | type, status, agent, risk, asset_id | 查询能力资产 |
| `check_role` | role_id, version | 角色完整性检查 |
| `run_resolution` | gap_name, gap_description | 单缺口能力解析 |
| `handoff_role` | from_role_id, to_role_id, contract_id, context, handoff_reason | 创建角色交接记录 |
| `submit_event` | source, agent, event_type, evidence, contract_id, role, session | 提交事件到账本 |
| `list_handoffs` | role_id, contract_id | 列出交接记录 |

### 4.3 CLI 查询命令

```bash
argus query contract <contract_id> [--store .argus]   # 查询合约及关联 handoffs
argus query role <role_id> [--store .argus]            # 查询角色及关联 packs 和 handoffs
argus mcp-serve --store .argus                          # 启动 MCP stdio 服务
```

### 4.4 Handoff Python API

```python
# HandoffManager
class HandoffManager:
    def __init__(self, handoffs_dir: Path) -> None
    def create(self, *, from_role_id, to_role_id, contract_id, context, handoff_reason) -> HandoffRecord
    def load(self, handoff_id: str) -> HandoffRecord | None
    def list_by_contract(self, contract_id: str) -> list[HandoffRecord]
    def list_by_role(self, role_id: str) -> list[HandoffRecord]
    def list_all(self) -> list[HandoffRecord]
```

## 5. Storage

- 事件账本：`.argus/ledger/events.json` — `AppendOnlyJsonlStore`（Phase 2 创建）
- 交接记录：`.argus/handoffs/{handoff_id}.json` — 扁平文件，每个记录一个 JSON 文件
- MCP 不产生独立存储文件——所有读写委托给 `QueryApplication` 的各存储层
- 转录导入：通过 `TranscriptIngestor`（Codex）或逐行解析（Claude）将转录数据写入 EventLedger
- 无新增存储格式需求

## 6. Governance and Security

- **MCP stdio 隔离**：日志输出到 stderr，JSON-RPC 响应输出到 stdout，信道完全分离（`_log` 函数写入 `sys.stderr`）
- **未知工具/方法返回标准 JSON-RPC 错误**：`-32601`（未知 method/tool），`-32603`（工具执行异常），避免信息泄漏
- **非法 JSON 行静默跳过**：MCP serve 循环中非法的 JSON 行不崩溃服务，保证健壮性
- **交接记录内容寻址**：`HandoffRecord.id = f"handoff-{sha1(payload)[:16]}"`，相同内容的交接幂等创建
- **适配器字段兼容**：ClaudeAdapter 字段映射 (`type || event_type`, `message || raw`, `session_id || session`)，兼容不同转录格式变体
- **批量导入保护**：Claude 转录导入中 JSON 解析失败抛出 `ValueError` 并携带行号；Codex 转录导入依赖 `TranscriptIngestor` 的错误处理

## 7. Failure Modes

- MCP 客户端发送非法 JSON：serve 循环捕获 `json.JSONDecodeError` 并 continue，不中断服务
- 调用未注册的 MCP 工具：返回 `{"error": {"code": -32601, "message": "unknown tool: <name>"}}`
- 工具执行时内部异常：返回 `{"error": {"code": -32603, "message": "<exception_str>"}}`
- 请求不包含 `id` 字段：`req_id = request.get("id")` 返回 None，响应中 `"id": null`（JSON-RPC 通知语义）
- 适配器转录文件格式损坏：Claude JSONL 非法行抛出 `ValueError(f"invalid transcript JSONL at line {line_number}: {exc.msg}")`
- 交接目录不存在/为空：`list_all()` 返回空列表（`handoffs_dir.exists()` 为 False 时直接返回 `[]`）
- 按 ID 加载不到的交接记录：`load(handoff_id)` 返回 None

## 8. Test Strategy

- Unit Tests：
  - `BaseAdapter` ABC 实例化被阻止（抽象类不可直接实例化）
  - `CodexAdapter.normalize_event` 输入输出映射正确性
  - `ClaudeAdapter.normalize_event` 字段回退逻辑（`type` → `event_type`，`message` → `raw`，`session_id` → `session`）
  - `HandoffRecord.create` 相同输入产生相同 ID（幂等性）
  - `HandoffRecord.to_dict()` / `from_dict()` 序列化往返
  - `MCPServer._handle` 对各 method 的分发正确性
- Integration Tests：
  - MCP 协议握手（initialize → tools/list → tools/call）完整流程
  - `ClaudeAdapter.ingest_transcript` 从 JSONL fixture 文件导入
  - `QueryApplication` 跨领域查询（合约+handoffs 关联）
  - `HandoffManager` 创建 → 加载 → 按维度筛选 完整链路
- Acceptance Tests：
  - MCP 服务器启动后可正常处理 initialize 和 tools/list 请求
  - `argus mcp-serve --store <dir>` 启动不报错
  - `argus query contract <id>` 返回关联的 handoffs
  - 对不存在角色的交接创建正常返回结果（不需要角色物理存在校验）

## 9. Compatibility

- `QueryApplication` 依赖 Phase 1-7 所有存储模块（ContractStorage, EventLedger, LearningLedger, CapabilityInventory, CapabilityPackStore, RolePackStore, HandoffManager），需确保这些模块已正确初始化
- `BaseAdapter` 定义为 ABC，所有现有和未来的适配器实现均需继承此基类，保证接口契约一致
- MCP 协议版本硬编码为 `"2024-11-05"`，未来需评估升级路径
- `QueryApplication` 同时服务 CLI 和 MCP 两种消费方式，新增查询能力时需同时更新两端的参数定义
- 转录文件导入（`ingest_transcript`）直接写入 `EventLedger`，与 Phase 2 的 `TranscriptIngestor` 共享存储

## 10. Open Questions

- MCP 工具的 `inputSchema` 当前统一为 `{"type": "object", "properties": {}, "additionalProperties": True}`，是否需要为每个工具提供精确的参数 schema？
- 是否需要支持更多 Agent 适配器（如 OpenAI、Gemini）？当前仅实现 Codex 和 Claude
- MCP 协议版本 (2024-11-05) 升级到更新版本时的兼容策略是什么？
- `QueryApplication` 的 `query_contracts` 中 workspace 参数已声明但未实现过滤逻辑——是否可以移除或补全？
- MCP 服务器是否需要支持资源 (resources) 和提示 (prompts) 能力，而非仅限于工具 (tools)？
