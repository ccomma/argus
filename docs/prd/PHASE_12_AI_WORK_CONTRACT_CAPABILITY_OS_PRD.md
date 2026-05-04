# Phase 12: AI Work Contract & Capability OS PRD

> Context loading: 新会话默认先读 `docs/context/CURRENT_HANDOFF.md`，再按需读取本 PRD。本文件只回答产品问题，不承担实现任务管理。

## 1. Background

经过 Phase 1-11 的逐步构建，Argus 已从追问式工作契约 MVP 演进为覆盖个人治理、团队治理、策略自动化和 Web 工作台的完整工具链。Phase 12 是 roadmap 的终章，目标是将 Argus 从"治理工具集合"提升为"AI 工作契约与能力操作系统"：引入资产生命周期状态机确保每个能力的创建、激活、禁用、隔离、弃用、归档和删除都有明确规则和审计追踪；通过多注册中心索引支持跨来源的能力发现；建立闭环反馈机制让 agent 执行结果反向驱动能力资产的提升、修订或弃用决策。

## 2. Users and Jobs

目标用户：

- 需要长期维护大量能力资产的组织，要求每个资产的状态变更可追踪、可验证、可回滚。
- 需要从多个注册中心（本地、团队、社区、企业）发现和管理能力的平台运营者。
- 希望 Agent 执行效果能自动反馈到能力资产质量评分的系统设计者。

用户任务：

- 通过状态机管理资产从创建到删除的完整生命周期。
- 查询资产的合法操作和状态转换历史。
- 在多注册中心索引中按名称、类型、标签、质量和风险评分搜索能力条目。
- 记录 agent 执行的成功、失败和纠正反馈信号。
- 基于反馈信号计算净评分（net_score），自动生成 promote/revise/review_or_deprecate/observe 推荐。

## 3. Problem

当前问题：

- 资产状态管理缺乏统一的状态机约束：不同模块对 active/disabled/deprecated/archived 的转换规则不一致。
- 能力发现仅限本地库存和外部只读建议，无法统一管理多个注册中心的条目索引。
- Agent 执行效果（成功/失败/纠正）与能力资产的质量评分之间没有闭环：用户不知道哪些能力真的有效，哪些应该替换。
- 缺乏对每个资产完整生命周期的审计追踪，无法回答"谁在什么时候为什么改变了这个能力的状态"。

## 4. Goals

- 实现资产生命周期状态机：7 种状态（DRAFT/ACTIVE/DISABLED/ISOLATED/DEPRECATED/ARCHIVED/DELETED），9 种操作（CREATE/ACTIVATE/DISABLE/ISOLATE/RELEASE/DEPRECATE/ARCHIVE/DELETE/ROLLBACK），19 条合法转换规则。
- 构建生命周期审计账本（LifecycleLedger）：append-only JSONL 格式，完整记录每次状态变更的操作者、原因、证据和时间戳。
- 实现多注册中心能力索引（RegistryIndex）：支持多维度搜索（名称子串、类型精确、标签 OR、质量下限、风险上限），结果按质量降序、风险升序排列。
- 构建闭环反馈系统（FeedbackLoop）：接收 success/failure/correction 三类信号，计算 net_score = promote - demote - (revise * 0.5)，产出四级推荐（promote/review_or_deprecate/revise/observe）。
- FeedbackSignal 持久化为独立 JSON 文件，支持按目标类型、目标 ID 和信号类型筛选。

## 5. Non-goals

- 不实现自动化状态变更（如"连续 30 天未使用自动归档"），状态转换仅通过显式 API 调用触发。
- 不做外部注册中心的实时同步和爬取（如定时拉取 Skillsmith 最新条目），索引条目由用户或 adapter 手动添加。
- 不实现基于反馈的自动能力修改（如自动替换低评分 skill），推荐仅作为建议，不自动执行。
- 不做复杂的 ML 反馈模型（如信号衰减、时序加权），当前采用简单均值聚合和阈值决策。

## 6. Core User Flows

核心流程 1 -- 管理资产生命周期：
1. 用户创建新资产，系统调用 state_machine_for(status) 创建状态机，初始状态为 DRAFT。
2. 用户通过 state_machine.available_actions() 查看当前状态下可执行的操作。
3. 用户执行 state_machine.apply(LifecycleAction.ACTIVATE)，状态从 DRAFT 转为 ACTIVE。
4. 如果尝试非法操作（如从 ACTIVE 直接 DELETE），state_machine.apply() 抛出 ValueError。
5. 每次状态变更，系统自动生成 LifecycleRecord（含 record_id、asset_id、action、from_state、to_state、triggered_by、reason、evidence、timestamp）。
6. LifecycleLedger.append() 将记录追加写入 JSONL 文件。

核心流程 2 -- 多注册中心能力发现：
1. 用户从不同来源（本地扫描、团队编目、外部市场）收集 RegistryEntry 条目，添加至 RegistryIndex。
2. 用户调用 index.search(name="python", entry_type="skill", tags=["code-generation"], min_quality=0.5, max_risk=0.5) 进行多维度搜索。
3. RegistryIndex 应用五层过滤（名称子串、类型精确、标签 OR、质量下限、风险上限），结果按 (-quality_score, risk_score) 排序返回。
4. RegistryIndex.save() 持久化索引为 JSON 文件。

核心流程 3 -- 闭环反馈驱动治理推荐：
1. Agent 执行任务后，系统调用 feedback_loop.record() 记录反馈信号：source_type="agent"，source_id=agent_id，signal_type="success|failure|correction"，target_type="capability|role|pack"，target_id=asset_id，strength=0.0-1.0，evidence={...}。
2. FeedbackSignal 持久化为 {signal_id}.json。
3. 用户调用 feedback_loop.compute_recommendation(target_type, target_id) 计算治理推荐。
4. FeedbackLoop 聚合 target 的所有 success/failure/correction 信号强度，计算 net_score。
5. 推荐逻辑：
   - net_score > 0.3 且信号数 >= 3：promote（建议推广）。
   - net_score < -0.3：review_or_deprecate（审查或弃用）。
   - revise_strength > 0.3：revise（需要修订）。
   - 其他情况：observe（数据不足，继续观察）。
6. 用户根据推荐决定对该资产的治理动作。

## 7. Success Criteria

- 状态机 TRANSITIONS 表覆盖 7 种状态和 19 条合法转换规则，非法操作抛出 ValueError。
- LifecycleLedger 支持追加记录和按 asset_id 筛选历史记录。
- RegistryIndex.search 正确执行五层过滤和双键排序（质量降序、风险升序）。
- 同一 (entry_id, source) 的 RegistryEntry 重复添加时原地替换，不产生重复条目。
- FeedbackLoop 正确聚合三类信号强度，net_score 计算公式正确。
- compute_recommendation 在正信号占优（net_score > 0.3，信号 >= 3）时产出 promote，负信号占优（net_score < -0.3）时产出 review_or_deprecate。
- FeedbackSignal 持久化后可通过 list_signals 按维度筛选完整恢复。

## 8. Risks and Open Questions

风险：

- 状态机的 19 条转换规则是当前设计快照，随着资产类型增加可能需要扩展，扩展时需确保不引入矛盾转换（如同时允许 A->B 和 A->C 但 B 和 C 互斥）。
- 闭环反馈的推荐阈值（net_score > 0.3、信号数 >= 3）基于经验设定，缺乏实证校准，可能在真实数据上产生过多 observe 或过少 promote。
- 多注册中心索引的条目质量评分（quality_score）和风险评分（risk_score）当前由条目创建者手动设定，缺乏自动评估机制，可能导致评分失真。
- FeedbackSignal 以独立 JSON 文件存储，信号量大时（数万条）文件系统性能可能成为瓶颈。

开放问题：

- 是否需要为状态机引入复合操作（如"归档并通知所有引用者"）？
- 多注册中心是否需要支持条目过期和自动刷新机制？
- 闭环反馈的 net_score 是否需要引入信号衰减因子（越旧的信号权重越低）？
- 推荐产出的 promote/revise 是否应与 Phase 7 的受控修改流程对接，形成完整的"反馈 -> 推荐 -> 修改 -> 回滚"闭环？
