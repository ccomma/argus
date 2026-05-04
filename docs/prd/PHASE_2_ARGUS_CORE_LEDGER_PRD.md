# Phase 2: Argus Core 事件与候选学习账本 PRD

> 上下文加载：新会话默认先读 `docs/context/CURRENT_HANDOFF.md` 和阶段 `HANDOFF.md`。本文件只回答 Phase 2 的产品需求和验收口径，不承担执行状态管理。

## 1. 背景

Phase 1 已经证明工作契约可以从模糊意图进入本地 CLI 闭环，并留下 `contract.json`、`contract.md`、`deliverables/`、`evaluations/` 和 `evidence.jsonl`。

Phase 2 的目标是补上 Argus Core 的学习底座：把工作契约、执行证据、会话记录、失败、纠正和成功路径统一进入仅追加账本，再从事件中生成候选学习项。

## 2. 用户与任务

目标用户：

- 继续使用 Argus 本地 CLI 的 AI 重度用户。
- 希望知道 agent 从真实工作中学到了什么的开发者和维护者。
- 后续 Phase 3 能力资产扫描和 Phase 4 能力包的消费者。

用户任务：

- 导入 Codex 会话记录或本地会话导出。
- 从 `.argus/contracts/*/evidence.jsonl` 导入工作契约执行证据。
- 查看仅追加事件账本。
- 查看候选学习项，而不是直接污染长期 memory / rules。
- 生成本地学习报告。

## 3. 问题

当前问题：

- Phase 1 有执行证据，但还没有统一事件账本。
- 工作契约中的返工、验收失败和用户纠正还不能被系统学习。
- 如果直接把事件写入 memory 或 rule，容易产生长期行为污染。
- 后续能力管理需要知道能力缺口来自哪些证据。

## 4. 目标

本阶段目标：

- 定义并实现 `EventRecord` 模式。
- 定义并实现 `CandidateLearningItem` 模式。
- 将 Phase 1 契约证据导入事件账本。
- 支持导入 Codex 会话记录测试集。
- 从事件中抽取候选学习项。
- 输出本地学习报告。
- 保持仅追加，不自动修改任何长期能力资产。

## 5. 非目标

本阶段不做：

- 不自动写入 memory、skill、rules、AGENTS.md 或 MCP config。
- 不做完整能力清单。
- 不做能力安装、删除、合并或回滚。
- 不做团队共享账本。
- 不做向量检索或复杂知识图谱。

## 6. 核心用户流程

### 流程 1：导入工作契约证据

1. 用户运行 `argus ledger ingest-contract <contract-id>`。
2. Argus 读取该契约的 `evidence.jsonl`。
3. Argus 生成仅追加 `EventRecord`。
4. 用户可以查看事件数量和导入摘要。

### 流程 2：导入会话记录测试集

1. 用户运行 `argus ledger ingest-transcript path/to/transcript.jsonl`。
2. Argus 标准化会话记录事件。
3. Argus 写入事件账本。

### 流程 3：生成候选学习项

1. 用户运行 `argus learning extract`。
2. Argus 扫描事件账本。
3. Argus 对用户纠正、命令失败、验收失败、重复模式生成候选学习项。
4. 用户查看候选项和证据引用。

### 流程 4：输出学习报告

1. 用户运行 `argus learning report`。
2. Argus 汇总事件类型、候选学习项、置信度、反向学习目标和风险。
3. 用户得到本地 Markdown/JSON 报告。

## 7. 验收标准

- 能从 Phase 1 `.argus/contracts/*/evidence.jsonl` 生成事件账本。
- 能从固定 Codex 会话记录测试集生成稳定事件。
- 能区分原始事件和候选学习项。
- 能从验收失败或用户纠正中生成带证据引用的候选学习项。
- 能输出本地学习报告。
- 不自动修改任何 memory、skill、rule、plugin、MCP 或全局配置。

## 8. 风险与开放问题

风险：

- 会话记录格式可能变化，适配器需要保持松耦合。
- 早期候选学习抽取可能比较规则化，不能过度承诺智能归因。
- 账本若不可追踪，会影响后续能力治理可信度。

开放问题：

- Codex 会话记录第一版支持哪几类事件字段。
- 候选学习置信度初版采用哪些启发式。
- 报告第一版以 Markdown 为主还是 JSON 为主。
