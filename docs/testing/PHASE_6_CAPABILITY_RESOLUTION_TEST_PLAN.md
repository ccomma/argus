# Phase 6: 能力解析 Test Plan

> Context loading: 新会话默认先读 `docs/context/CURRENT_HANDOFF.md`，再按需读取本测试计划。当前验收状态写入阶段目录的 `ACCEPTANCE.md`。

## 1. Scope

本测试计划覆盖：

- 决策枚举（Decision）与风险映射（DECISION_RISK）的正确定义
- 四级匹配策略：REUSE（精确复用）、CONFIGURE（配置现有）、CREATE_LOCAL（参照新建）、INSTALL_SUGGESTED（外部安装）
- 多源缺口输入：手动传入、学习项反向目标、能力包缺失建议、治理发现
- 解析结果确定性（相同输入产生相同输出）
- 按 gap_id 去重
- ResolutionReporter 双格式（Markdown + JSON）报告生成
- CLI `resolve run` 与 `resolve report` 命令

不覆盖：

- 实际外部能力安装执行
- 跨系统能力同步
- 增量解析性能优化

## 2. Fixtures

固定样例：

- 单个 skill 资产（research）：用于精确匹配和去重测试
- 单个 mcp_server 资产（browser-automation）：用于相似匹配测试
- 混合类型多重资产：用于部分匹配和边界测试

## 3. Unit Tests

- `test_decision_enum_and_risk_mapping`：验证 Decision 枚举值字符串正确，DECISION_RISK 映射 low/medium/high 正确
- `test_gap_with_exact_local_match_yields_reuse_decision`：精确关键词匹配 -> REUSE，risk_level=low，confidence>=0.8
- `test_gap_with_partial_match_yields_configure_decision`：部分关键词重叠 -> CONFIGURE，risk_level=low
- `test_gap_with_no_local_match_yields_install_suggested`：无本地匹配 -> INSTALL_SUGGESTED，risk_level=high，matched_local_asset_ids 为空
- `test_gap_with_similar_local_capability_yields_create_local`：弱相似（分数在 (0, 0.15) 区间）-> CREATE_LOCAL
- `test_resolution_is_deterministic_for_same_inputs`：同一资产库、同一缺口两次解析得到相同决策和 matched_local_asset_ids
- `test_resolver_deduplicates_gaps_with_same_id`：同一 gap_id 多次出现仅保留第一条

## 4. Fixture Tests

- `test_resolve_from_learnings_extracts_capability_gaps`：反向学习目标为 capability_pack 的 CandidateLearningItem 被正确提取为缺口并解析
- `test_resolve_from_advice_creates_resolutions_per_missing_capability`：缺失能力名称列表逐一解析，全部 INSTALL_SUGGESTED
- `test_resolve_from_findings_handles_dedupe_and_risk_categories`：dedupe/risk 类治理发现被解析，work_contract 类被忽略

## 5. Integration Tests

- `test_resolution_reporter_writes_markdown_and_json`：ResolutionReporter 写出 Markdown 含 [reuse]/[install_suggested] 标记，JSON 含 summary.total_gaps 和 by_decision 统计
- `test_cli_resolve_run_and_report_commands`：`argus.cli resolve run` 输出 list 结果，`argus.cli resolve report` 输出含 markdown_path 和 json_path 的报告

## 6. Acceptance Tests

- 四级匹配策略在所有资产组合下输出正确 Decision 类型
- 报告生成不修改资产清单

## 7. Regression Risks

- resolver 算法对正常化输入产生意外决策：使用确定性测试验证
- 报告生成修改源数据：所有报告测试使用临时目录隔离
- 空资产库导致崩溃：resolve_from_advice 测试覆盖空清单输入

## 8. Test Commands

```bash
PYTHONPATH=src python -m pytest tests/test_phase6_capability_resolution.py -v
PYTHONPATH=src python -m unittest tests.test_phase6_capability_resolution.Phase6CapabilityResolutionTest
```
