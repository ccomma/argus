# Phase 1: 追问模式工作契约 MVP 技术设计

> 上下文加载：新会话默认先读 `docs/context/CURRENT_HANDOFF.md` 和阶段 `HANDOFF.md`。本文件只回答 Phase 1 的模块、接口、数据和风险边界，不记录每日执行状态。

## 1. 概述

Phase 1 实现一个本地优先的工作契约 MVP。系统接收用户的模糊意图，通过追问策略生成澄清性问题，计算完整度评分，生成工作契约，再根据交付物契约生成并验收结构化交付物。

第一版以文件和 CLI 为主，不依赖网络服务，不自动修改任何 agent 能力资产。

## 2. 架构

模块边界：

- `ArgusCore`：Phase 1 应用边界，CLI、未来 MCP server 和 adapter 都复用它，而不是复制业务编排逻辑。
- `ContractSession`：管理一次从意图到工作契约的会话状态。
- `QuestionStrategy`：定义必须补齐的信息、追问规则、提问预算和完成条件。
- `score_answers` / `CompletenessScore`：根据工作契约草稿计算信息完整度。
- `WorkContractBuilder`：将意图、用户回答和策略结果组装为工作契约。
- `DeliverableContract`：定义 PRD、阶段计划、研究计划等交付物的必备结构。
- `DeliverableRenderer`：从工作契约生成 PRD、roadmap、research plan 草案。
- `DeliverableEvaluator`：对照工作契约和交付物契约，检查交付物的缺失项。
- `ContractStorage`：读写本地工作契约、版本历史和执行证据。

主要数据流：

```text
intent
  -> ContractSession
  -> QuestionStrategy
  -> clarifying questions
  -> user answers
  -> score_answers
  -> WorkContractBuilder
  -> DeliverableContract
  -> DeliverableRenderer
  -> structured deliverable
  -> DeliverableEvaluator
  -> evaluation result
  -> ContractStorage
```

## 3. 数据模型

```text
WorkContract
- id: 稳定的本地标识符
- version: 整数或语义化版本号
- status: draft | clarifying | ready | executing | reviewing | done | superseded | archived
- intent: 用户的原始意图
- questioning_mode: quick | standard | strict
- goal: 目标成果
- context: 背景和相关情况
- audience: 目标读者或用户
- inputs: 可用的源材料
- outputs: 预期交付物
- non_goals: 明确排除在外的条目
- constraints: 时间、格式、技术、政策或资源约束
- risks: 已知的风险和假设
- confirmation_points: 需要用户确认的决策点
- acceptance_criteria: 验收输出的条件
- completion_definition: 完成定义
- role_or_work_mode: 可选的工作角色或模式
- capability_pack_ref: 可选的未来能力包引用
- completeness_score: 评分对象
- change_history: 版本变更记录
- execution_evidence: 生成的文件、检查项、确认记录、评估结果
```

```text
QuestionStrategy
- id: 策略标识符
- name: 策略名称
- mode: quick | standard | strict
- required_facts: 必须澄清的字段
- decision_points: 用户可能需要做的选择
- follow_up_rules: 何时继续追问
- question_budget: 最大问题数或追问轮数
- completion_criteria: 最低评分或必填字段
```

```text
CompletenessScore
- goal_score: 0-1
- context_score: 0-1
- input_score: 0-1
- output_score: 0-1
- constraint_score: 0-1
- risk_score: 0-1
- acceptance_score: 0-1
- overall_score: 0-1
- missing_fields: 缺失或薄弱的字段列表
- rationale: 简短说明
```

```text
DeliverableContract
- id: 交付物类型标识符
- deliverable_type: prd | roadmap | research_plan | technical_questions
- required_sections: 必须包含的输出章节
- acceptance_criteria: 针对此交付物的验收要求
- missing_item_policy: warn | block | ask_follow_up
```

```text
DeliverableEvaluation
- contract_id: 工作契约 ID
- deliverable_type: 被评估的交付物类型
- status: pass | partial | fail
- covered_items: 已满足的字段和标准
- missing_items: 未满足的字段和标准
- risks: 评估器警告
- suggested_follow_ups: 改进输出的追问或编辑建议
```

## 4. 接口

第一版推荐使用 CLI：

```text
argus contract start --intent "<user intent>" --mode standard
argus contract draft --intent "<user intent>" --mode standard
argus contract score <contract-id>
argus contract render <contract-id> --type roadmap
argus contract evaluate <contract-id> <deliverable-path> --type roadmap
argus contract show <contract-id>
```

接口输出应支持人类可读的 Markdown 格式，同时保留结构化 JSON/YAML 以便后续测试和 Phase 2 ledger 消费。

## 5. 存储

Phase 1 使用本地文件存储，避免过早引入数据库。

建议目录结构：

```text
.argus/
  contracts/
    <contract-id>/
      contract.json
      contract.md
      versions/
      deliverables/
      evaluations/
      evidence.jsonl
```

读写边界：

- 只写入项目本地 `.argus/` 目录。
- 不写入全局 agent 配置。
- 不写入 skill、MCP、plugin、rule 或 memory。
- 所有持久化输出应可删除、可重建、可被后续 Phase 2 导入。

迁移策略：

- Phase 1 schema 携带 `schema_version` 字段。
- 破坏性 schema 修改必须提供简单的 migration 或明确的重建方式。

## 6. 治理与安全

Phase 1 应保持低风险等级。

允许自动执行的操作：

- 生成本地工作契约。
- 生成本地交付物草案。
- 生成本地评估报告。
- 写入项目本地 `.argus/` 目录。

禁止自动执行的操作：

- 安装外部依赖或能力。
- 修改全局 rule、memory、skill、MCP config、plugin config。
- 删除能力资产。
- 自动将契约内容提升为长期行为规则。

审计要求：

- 每次契约版本变更应记录时间、原因和摘要。
- 评估结果应进入执行证据。
- 用户确认点必须保留确认状态。

## 7. 失败模式

需要处理的失败模式：

- 用户意图过短，无法生成有效追问。
- 用户跳过关键问题，完整度评分不足。
- 追问预算用尽但契约仍不完整。
- 交付物缺少必备章节。
- 契约文件损坏或 schema version 不兼容。
- 多次运行产生重复的 contract ID。
- 输出路径不可写。

## 8. 测试策略

本阶段测试策略：

- 单元测试：数据模型校验、完整度评分、追问预算、状态流转、评估器缺失项判断。
- Fixture 测试：固定模糊意图、固定用户回答、固定交付物，验证稳定的工作契约和评估结果。
- 集成测试：从意图到追问、契约、交付物、评估、存储的完整流程。
- 验收测试：按 PRD 验收标准，使用真实 Argus 项目场景手动或自动确认。

## 9. 兼容性

Phase 1 不影响已有的 ledger、配置或外部 agent adapter。它只新增本地工作契约数据，为 Phase 2 的事件账本和候选学习账本提供输入。

后续兼容要求：

- `WorkContract.id` 和 `version` 必须稳定。
- `execution_evidence` 应能被 Phase 2 作为事件证据引用。
- `capability_pack_ref` 可以为空，但字段须保留。

## 10. 待解决问题

- 第一版已同时支持交互式 `contract start` 和非交互式 `contract draft`。
- 第一版结构化存储采用 JSON，审计证据采用 JSONL，交付物采用 Markdown。
- 第一版不引入 LLM provider，先用规则和模板证明数据流。
- `.argus/` 已加入 `.gitignore`。
