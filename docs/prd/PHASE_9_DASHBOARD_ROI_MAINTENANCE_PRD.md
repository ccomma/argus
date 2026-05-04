# Phase 9: Dashboard、ROI 与维护任务 PRD

> Context loading: 新会话默认先读 `docs/context/CURRENT_HANDOFF.md`，再按需读取本 PRD。本文件只回答产品问题，不承担实现任务管理。

## 1. Background

Phase 8 已完成跨 Agent Adapter 和 MCP Server，使 Argus 成为 runtime-neutral 的治理核心。Phase 9 要回答一个关键问题：工作契约、角色和 agent 是否真的在变强？用户需要看到治理活动的效果，而非仅仅相信系统在运作。本阶段承接 roadmap 中 Phase 8 的跨角色查询能力，将合约、学习、角色三个维度的数据转化为可量化、可对比的 ROI 指标，同时引入系统化的维护任务引擎，确保能力资产库不会随着时间积累而腐化。

## 2. Users and Jobs

目标用户：

- 长期使用 Argus 管理多个工作契约和角色的重度 AI 产出者。
- 需要向自己或团队证明 AI 辅助效率是否提升的个人用户。
- 需要定期清理过期、冲突、未使用能力资产的维护者。

用户任务：

- 查看合约、学习、角色三个维度的量化 ROI 报告。
- 在本地仪表盘中查看治理全貌。
- 发现并处理重复资产、冲突资产、废弃资产和未使用的能力包/角色包。
- 将仪表盘和维护报告用于决策：哪些合约模板值得保留，哪些角色需要更新，哪些资产该清理。

## 3. Problem

当前问题：

- 工作契约、学习项、角色和能力包分散在多个存储后端，用户无法一次性看到"治理效果如何"。
- 能力资产库随时间积累会产生重复定义、相互冲突的资产和无人使用的包，缺乏系统化检测手段。
- Phase 5 的治理报告关注单次快照的发现问题，但没有趋势对比和效率度量。
- 维护动作（去重、归档、废弃标记）缺乏统一的健康检查入口，用户不知道"从哪里开始清理"。

## 4. Goals

- 提供合约 ROI、学习 ROI、角色 ROI 三大维度的量化指标计算。
- 生成本地仪表盘报告（Markdown + JSON 双格式），供人工审阅和程序消费。
- 构建维护引擎，自动检测六类问题：重复资产、冲突资产、废弃资产、归档资产、未使用能力包、未使用角色包。
- 维护报告同样输出 Markdown + JSON 双格式，支持趋势对比和告警集成。
- CLI 命令 `argus dashboard` 和 `argus maintenance` 一键生成报告。

## 5. Non-goals

- 不做在线 Dashboard 或实时监控面板（实时 Web UI 属于 Phase 10）。
- 不自动执行清理动作（archive、delete、merge），仅做检测和建议。
- 不做跨时间段趋势分析和历史对比图表。
- 不计算财务 ROI（如时间成本换算为金额）。

## 6. Core User Flows

1. 用户运行 `argus dashboard`。
2. Argus 读取合约存储、事件账本、学习账本、资产清单、能力包存储、角色包存储和交接管理器七个数据源。
3. ROICalculator 分别计算 contract_roi（合约总量、状态分布、平均完整性、问询轮次、交付物通过率）、learning_roi（学习项总量、类型/作用域分布、平均置信度、审核状态）、role_roi（角色总量、交接次数、活跃角色、平均能力包数）。
4. DashboardReporter 将三大维度指标写入 `dashboard.md` 和 `dashboard.json`。
5. 用户运行 `argus maintenance`。
6. MaintenanceEngine 扫描全量资产：检测重复、冲突、废弃、归档资产，标记未绑定到合约的能力包，列出所有角色包供审查。
7. MaintenanceReporter 将六类发现写入 `maintenance.md` 和 `maintenance.json`。
8. 用户审阅两份报告，决定下一步治理动作。

## 7. Success Criteria

- ContractROI 包含 total_contracts、by_status、avg_completeness、avg_question_rounds、total_change_history_entries、deliverable_pass_rate 六项指标。
- LearningROI 包含 total_learnings、by_type、by_scope、avg_confidence、pending_count、promoted_count 六项指标。
- RoleROI 包含 total_roles、total_handoffs、roles_used_in_handoffs、avg_packs_per_role 四项指标。
- 仪表盘报告生成 dashboard.md 和 dashboard.json 两个文件。
- 维护引擎覆盖 duplicates、conflicts、deprecated_assets、archived_assets、unused_capability_packs、unused_role_packs 六类问题。
- 维护报告生成 maintenance.md 和 maintenance.json 两个文件。
- 所有计算仅读取数据，不修改任何资产、合约或角色。

## 8. Risks and Open Questions

风险：

- ROI 指标依赖事件账本中的 deliverable_evaluated 事件，如果事件记录不完整，交付物通过率可能为 0 或无意义。
- 维护引擎的 unused_role_packs 检测当前仅将所有角色包标记为待审查，未实现基于交接记录的使用判断，可能产生误报。
- 重复和冲突检测依赖资产分析的启发式函数（find_potential_duplicates/find_potential_conflicts），对于边界情况可能漏检或误检。

开放问题：

- 是否需要引入时间窗口参数（如"最近 30 天"）来过滤 ROI 计算范围？
- 维护引擎的"未使用角色包"判断标准何时从"全部标记"升级为"基于交接记录的真实判断"？
- 仪表盘是否需要合并维护摘要（当前 DashboardReporter.write 已支持可选的 maintenance_summary 参数）？
