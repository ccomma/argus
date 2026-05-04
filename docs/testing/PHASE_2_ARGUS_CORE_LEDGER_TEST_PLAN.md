# Phase 2: Argus Core 事件与候选学习账本 测试计划

> 上下文加载：新会话默认先读 `docs/context/CURRENT_HANDOFF.md` 和阶段 `HANDOFF.md`。本文件仅回答 Phase 2 的测试策略；实际验收证据记录在阶段 `ACCEPTANCE.md`。

## 1. 范围

本测试计划覆盖：

- EventRecord 模型。
- CandidateLearningItem 模型。
- Phase 1 契约证据导入（contract evidence ingestion）。
- Codex 会话记录样例导入。
- 事件账本（event ledger）只追加（append-only）行为。
- 候选学习项提取。
- 学习报告。

不覆盖：

- 能力清单（capability inventory）。
- 外部能力安装。
- memory / rule 自动提升。
- 团队共享账本。

## 2. 固定样例

- `phase1_contract_evidence_pass.jsonl`：交付物渲染与评估均通过。
- `phase1_contract_evidence_fail.jsonl`：评估结果为 partial/fail。
- `codex_user_correction.jsonl`：用户明确纠正 agent。
- `codex_command_failed_recovered.jsonl`：命令失败后修复。
- `codex_task_succeeded.jsonl`：任务成功完成。

## 3. 单元测试

- `EventRecord`：必填字段、event type、证据引用校验。
- `EventLedger`：只追加写入，读取顺序稳定。
- `CandidateLearningItem`：status、confidence、evidence_refs 校验。
- `LearningExtractor`：不同事件类型生成正确的 learning type。

## 4. 样例测试

- contract evidence pass：生成 `deliverable_evaluated` 事件但不生成高风险学习项。
- contract evidence fail：生成 `deliverable_gap` 候选学习项。
- user correction：生成 `correction` 候选学习项。
- command failed recovered：生成 `tool_pitfall` 或 `workflow_pattern` 候选学习项。

## 5. 集成测试

- 使用 Phase 1 CLI 生成契约、渲染、评估，再导入契约证据。
- 从事件账本提取候选学习项。
- 生成学习报告。

## 6. 验收测试

- 能从真实 Phase 1 `.argus/contracts/*/evidence.jsonl` 生成事件账本。
- 能从固定会话记录样例生成稳定事件。
- 能区分原始事件（raw event）和候选学习项（candidate learning item）。
- 没有自动写入 memory、skill、rules、role profile 或 agent 全局配置。

## 7. 回归风险

- 重复导入同一证据：验证 event id 或去重键。
- 会话记录格式变化：未知字段必须被保留或安全忽略。
- 学习项提取过度自信：低证据事件 confidence 不应过高。
- 账本被覆盖：必须覆盖只追加测试。

## 8. 测试命令

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
python3 -m compileall -q src tests
git diff --check
```
