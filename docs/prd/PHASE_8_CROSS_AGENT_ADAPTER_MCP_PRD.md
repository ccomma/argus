# Phase 8: 跨 Agent 适配器与 MCP 服务 PRD

> Context loading: 新会话默认先读 `docs/context/CURRENT_HANDOFF.md`，再按需读取本 PRD。本文件只回答产品问题，不承担实现任务管理。

## 1. Background

Phase 1-7 的核心模型——工作契约、事件账本、能力资产、能力包、治理报告、能力解析、受控修改——都是 runtime-neutral 的。但在 Phase 8 之前，Argus 只通过 CLI 暴露功能，且事件来源路径与 Codex 目录结构紧密耦合。

Phase 8 的目标是三个层面同时打开：一是通过抽象适配器层让不同 AI Agent（Codex、Claude 等）的事件能进入同一套账本；二是通过 MCP JSON-RPC 服务让外部 agent 能在运行时查询合约、角色、学习项、资产，并执行角色交接；三是建立角色交接记录机制，支撑围绕同一工作契约的多角色接力。

## 2. Users and Jobs

目标用户：

- 运行多个 AI Agent（Codex、Claude Code 等）并希望统一治理的开发者。
- 需要通过 MCP 协议在 agent 会话中动态查询 Argus 状态的用户。
- 需要在同一工作契约下进行角色交接（如市场研究员->产品经理->架构师）的项目负责人。

用户任务：

- 将 Codex 或 Claude 的转录数据批量导入 Argus 事件账本。
- 通过 MCP 工具的 stdio JSON-RPC 接口查询合约、角色、能力包、学习项和资产。
- 在 agent 会话中通过 MCP 检查角色可用性、执行能力解析。
- 记录角色间的上下文交接，形成完整的角色接力链路。
- 提交原始事件到 Argus 账本，不限 agent 来源。

## 3. Problem

当前问题：

- 事件导入逻辑与 Codex 转录格式紧耦合，Claude Code 等其他 agent 的转录数据无法直接导入。
- Argus 缺乏运行时查询接口——agent 在会话中无法查询已有工作契约、角色能力包或学习项。
- 多角色围绕同一工作契约的协作缺少交接记录机制——角色切换后上下文丢失。
- Argus 核心模型是 runtime-neutral 的，但外部接入点只有 CLI。

## 4. Goals

- 定义 BaseAdapter 抽象基类，统一"外部原始事件 -> Argus EventRecord"的标准化契约。
- 实现 CodexAdapter（复用现有 TranscriptIngestor）和 ClaudeAdapter（处理 JSONL 格式和字段命名差异）。
- 实现基于 stdio 的 JSON-RPC 2.0 MCP 服务器，注册 10 个工具。
- 实现角色交接记录模型（HandoffRecord）和管理器（HandoffManager），支持内容寻址 ID 和按合约/角色筛选。
- 实现统一查询门面（QueryApplication），聚合五大领域查询，作为 MCP 服务和其他消费者的唯一入口。

## 5. Non-goals

- 不实现完整的 MCP 客户端 SDK（只做服务端）。
- 不做插件/extension 形态的适配器分发——adapter 是本地的 Python 模块。
- 不做 MCP 资源的 resources/list 和 resources/read（当前仅实现 tools）。
- 不做 agent 运行时交互（如直接调用 agent API）——adapter 只处理转录文件和原始事件。
- 不做团队多用户 MCP 服务。

## 6. Core User Flows

导入不同 Agent 的事件：

1. 用户将 Codex 转录文件路径传给 CodexAdapter，adapter 委托 TranscriptIngestor 逐行解析、标准化并批量写入账本。
2. 用户将 Claude JSONL 转录文件传给 ClaudeAdapter，adapter 逐行解析并处理字段映射差异（type -> event_type、message -> evidence、session_id -> session），遇非法 JSON 行时抛出带行号的错误。

MCP 服务启动与查询：

3. 用户（或 agent）启动 MCP 服务：`python -m argus.mcp --store .argus`。
4. MCP 客户端通过 stdio 发送 initialize 握手请求，服务端返回协议版本和能力声明。
5. Agent 在会话中通过 `tools/call` 调用任意注册工具，例如：
   - `query_contracts`：按 status、workspace、role_id 过滤合约，附带回其关联的角色交接记录。
   - `check_role`：检查指定角色在当前能力清单中的就绪状态，返回满足和缺失的能力包。
   - `run_resolution`：对命名缺口执行四级能力匹配解析。
   - `query_learnings`：按合约、类型、作用域、最低置信度过滤候选学习项。

角色交接：

6. Agent A（如市场研究员）完成任务后，通过 MCP 调用 `handoff_role` 创建一条交接记录，将上下文传递给 Agent B（如产品经理）。
7. HandoffManager 基于内容哈希生成幂等 ID，持久化为 JSON 文件。
8. Agent B 加载交接记录获取前序角色的上下文，继续在同一工作契约下工作。
9. 用户可通过 `list_handoffs` 按合约或角色查询完整交接链路。

事件提交：

10. 任意 agent 通过 MCP 调用 `submit_event` 提交原始事件，QueryApplication 提取标准字段构造 EventRecord 并写入事件账本。

## 7. Success Criteria

- 核心模型不依赖任一 agent 的目录结构或存储格式。
- CodexAdapter 和 ClaudeAdapter 均能批量导入对应格式的转录文件，产生标准化的 EventRecord。
- MCP 服务支持 10 个工具（query_contracts、query_roles、query_packs、query_learnings、query_assets、check_role、run_resolution、handoff_role、submit_event、list_handoffs），客户端可通过 stdio JSON-RPC 调用。
- QueryApplication 聚合五大查询维度，作为 MCP 和未来其他入口的统一门面。
- 角色交接记录支持内容寻址 ID、按合约和按角色筛选。
- MCP 服务在 `notifications/initialized` 通知和非法 JSON 行上保持健壮性（不崩溃）。

## 8. Risks and Open Questions

风险：

- BaseAdapter 接口较薄（仅 normalize_event + submit_event），未来如需支持更多事件类型（如工具调用、错误恢复）可能需要扩展。
- ClaudeAdapter 的字段映射基于对 Claude Code 转录格式的已知假设，格式变化需同步更新映射逻辑。
- MCP 服务当前为单进程 stdio 模式，不支持并发请求——同时多个客户端连接需要进程管理器或改为 socket 模式。

开放问题：

- 是否需要为更多 agent（如 Hermes、Cline、OpenAI Codex CLI）添加适配器？
- MCP 工具的参数 schema 当前为宽松的 `additionalProperties: true`，是否需要收紧为严格的 JSON Schema？
- 交接记录的上下文结构是否需要标准化（如强制包含关键决策、未决问题和交付物引用）？
- 是否需要 MCP 的 `resources/list` 支持以让 agent 浏览报告文件？
