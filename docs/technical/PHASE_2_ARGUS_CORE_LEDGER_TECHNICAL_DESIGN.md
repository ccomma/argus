# Phase 2: Argus Core 事件与候选学习账本 技术设计

> 上下文加载：新会话默认先读 `docs/context/CURRENT_HANDOFF.md` 和阶段 `HANDOFF.md`。本文件只回答 Phase 2 的模块、接口、数据和风险边界，不记录每日执行状态。

## 1. 概述

Phase 2 在 Phase 1 `ArgusCore` 之上增加事件账本和候选学习能力。核心目标是将工作契约的执行证据和 agent transcript 标准化为只追加的事件记录，再从事件中抽取候选学习项。

## 2. 架构

模块边界：

- `EventRecord`：标准化事件模型。
- `EventLedger`：只追加事件读写。
- `ContractEvidenceIngestor`：读取 Phase 1 契约的 `evidence.jsonl` 并生成事件。
- `TranscriptIngestor`：读取 Codex transcript fixture 并生成事件。
- `CandidateLearningItem`：候选学习项模型。
- `LearningExtractor`：从事件中生成候选学习项。
- `LearningLedger`：只追加候选学习项读写。
- `LearningReporter`：输出本地学习报告。

数据流：

```text
contract evidence / transcript
  -> ingestor
  -> EventRecord
  -> EventLedger
  -> LearningExtractor
  -> CandidateLearningItem
  -> LearningLedger
  -> LearningReporter
```

## 3. 数据模型

```text
EventRecord
- id: 稳定的事件标识符
- source: contract_evidence | codex_transcript | manual_fixture
- agent: codex | unknown | 未来的适配器名称
- contract_id: 可选的工作契约 ID
- contract_version: 可选的工作契约版本
- role: 可选的角色或工作模式
- workspace: 本地工作区路径
- session: 可用的会话标识符
- timestamp: 整数或 ISO 时间戳
- event_type: contract_created | deliverable_rendered | deliverable_evaluated | user_correction | command_failed | command_recovered | task_succeeded
- evidence: 精简的证据载荷
- execution_evidence: 文件路径、命令摘要、评估器状态、生成的产物
- risk_metadata: 风险与敏感度提示
```

```text
CandidateLearningItem
- id: 稳定的候选学习项 ID
- summary: 人类可读的学习摘要
- type: correction | tool_pitfall | workflow_pattern | capability_gap | user_preference | project_rule | deliverable_gap
- scope: user | project | domain | tool | agent | team
- confidence: 0-1
- evidence_refs: 关联的事件 ID 列表
- reverse_learning_target: question_strategy | deliverable_contract | role_playbook | capability_pack | none
- status: pending | accepted | rejected | promoted | superseded | expired
```

## 4. 接口

初期 CLI：

```text
argus ledger ingest-contract <contract-id>
argus ledger ingest-transcript <path>
argus ledger list
argus learning extract
argus learning list
argus learning report
```

## 5. 存储

Phase 2 继续使用本地文件存储：

```text
.argus/
  ledger/
    events.jsonl
    candidate_learnings.jsonl
    reports/
      learning-report.md
      learning-report.json
```

原则：

- `events.jsonl` 采用只追加写入。
- `candidate_learnings.jsonl` 采用只追加写入，状态变更通过新记录或替代记录来表达。
- 不写入全局 agent 配置。
- 不修改 Phase 1 契约的原始内容，只引用其执行证据。

## 6. 治理与安全

允许自动执行的操作：

- 读取本地 `.argus/` 中的契约证据。
- 读取用户指定的 transcript fixture。
- 写入本地账本和报告。
- 生成待审核的候选学习项。

禁止自动执行的操作：

- 自动将学习项提升为 memory、rule、skill 或配置。
- 自动安装或修改能力资产。
- 自动删除事件。

## 7. 失败模式

- 契约 ID 不存在。
- evidence.jsonl 损坏或包含未知字段。
- transcript fixture 格式不符合预期。
- 重复导入同一事件。
- 候选学习项的证据引用丢失。
- 账本为空时生成报告。

## 8. 测试策略

- 单元测试：事件 schema、候选学习项 schema、去重键、置信度评分。
- Fixture 测试：固定契约证据、固定 transcript fixture，生成稳定的账本。
- 集成测试：Phase 1 契约 -> 摄取 -> 抽取 -> 报告。
- 验收测试：覆盖成功会话、命令失败后修复、用户明确纠正、工作契约追问四类样例。

## 9. 兼容性

- 复用 Phase 1 `ArgusCore` 和 `.argus/contracts/` 存储。
- Phase 2 不改变 Phase 1 CLI 的输出结构。
- Phase 2 账本后续应能被 Phase 3 能力资产清单和 Phase 4 能力解析器使用。

## 10. 待解决问题

- transcript 摄取第一版是否只支持 JSONL，还是同时支持纯文本。
- 候选学习项状态变更是否采用只追加的替代记录方式。
- 报告是否需要包含隐私/敏感证据警告。
