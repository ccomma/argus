# Phase 12: AI 工作合约能力操作系统 Test Plan

> Context loading: 新会话默认先读 `docs/context/CURRENT_HANDOFF.md`，再按需读取本测试计划。当前验收状态写入阶段目录的 `ACCEPTANCE.md`。

## 1. Scope

本测试计划覆盖：

- 生命周期状态机：7 种资产状态的状态转换约束、可用操作查询和非法转换拦截
- 生命周期账本：变更记录的创建、追加写入（JSONL）和按资产 ID 筛选
- 能力注册中心：RegistryEntry 的创建/序列化、RegistryIndex 的多维度搜索、增删和持久化
- 反馈闭环：FeedbackSignal 的记录、多条件筛选、强度聚合和资产推荐决策
- CLI 命令：lifecycle show/apply/history、registry add/search/list、feedback record/list/recommend

不覆盖：

- 分布式注册中心同步
- 反馈信号的实时流处理
- 状态机可视化渲染
- 注册中心的外部源（非 local）集成

## 2. Fixtures

固定样例：

- 空临时目录：所有文件系统操作在 `tempfile.TemporaryDirectory()` 中执行
- 默认状态机：`StateMachine(AssetState.DRAFT)` 起始于 DRAFT 态
- 测试注册条目：`RegistryEntry("e1", "Python Tester", "skill", "local", quality_score=0.9, tags=["python"])`
- 状态转换表 TRANSITIONS：定义 DRAFT/ACTIVE/DISABLED/ISOLATED/DEPRECATED/ARCHIVED/DELETED 共 7 种状态的合法转换，其中 DELETED 为终态无任何出边
- 测试反馈信号：3 条 success 信号强度分别为 0.8/0.7/0.9，1 条 failure 信号强度为 -0.5，1 条修正信号强度为 0.6

## 3. Unit Tests

测试文件: `tests/test_phase12_operating_system.py`

- `Phase12LifecycleTest.test_state_machine_default_transitions`：DRAFT 态 can(ACTIVATE) 和 can(ARCHIVE) 为 True，can(DISABLE) 为 False
- `Phase12LifecycleTest.test_state_machine_apply`：DRAFT 态 apply(ACTIVATE) 后状态变为 ACTIVE，此时 can(DISABLE) 为 True
- `Phase12LifecycleTest.test_state_machine_invalid_transition`：ACTIVE 态 apply(CREATE) 抛出 ValueError
- `Phase12LifecycleTest.test_state_machine_available_actions`：ACTIVE 态可用操作包含 DISABLE/ISOLATE/DEPRECATE
- `Phase12LifecycleTest.test_state_machine_isolated_release`：ISOLATED 态 can(RELEASE) 为 True，apply 后回到 ACTIVE
- `Phase12LifecycleTest.test_deleted_no_transitions`：DELETED 态无可用操作（终态）
- `Phase12LifecycleTest.test_state_machine_for_string`：字符串 "active" 创建的状态机当前为 ACTIVE，"unknown" 回退为 DRAFT
- `Phase12LifecycleTest.test_lifecycle_record_create`：创建后 record_id 非空，asset_id 匹配，to_dict 中 action 为字符串 "activate"
- `Phase12LifecycleTest.test_lifecycle_ledger_append_and_list`：追加 2 条记录后 list_all 返回 2 条，for_asset 按资产筛选正确
- `Phase12RegistryTest.test_registry_entry`：创建条目后 to_dict/from_dict 往返 name 一致
- `Phase12RegistryTest.test_registry_index_add_and_search`：按 name 搜索返回 1 条，按 entry_type 搜索返回 2 条，按 max_risk 过滤排除高风险条目
- `Phase12RegistryTest.test_registry_index_remove`：移除后条目数为 0，再次移除返回 False
- `Phase12RegistryTest.test_registry_index_save_and_load`：保存后加载条目数一致
- `Phase12FeedbackTest.test_feedback_record_signal`：record 返回的 signal 含非空 signal_id
- `Phase12FeedbackTest.test_feedback_list_and_filter`：按 target_type+target_id 筛选返回 2 条，按 signal_type 筛选返回 2 条 success
- `Phase12FeedbackTest.test_feedback_aggregate_strength`：2 条 success 信号（0.8+0.6）聚合平均值为 0.7
- `Phase12FeedbackTest.test_feedback_recommendation_promote`：3 条 success 信号（均 >=0.7）后推荐结果为 "promote"
- `Phase12FeedbackTest.test_feedback_recommendation_observe_empty`：无信号目标的推荐结果为 "observe"，total_signals=0

## 4. Fixture Tests

- ACTIVE 状态的合法转换：DISABLE=>DISABLED, ISOLATE=>ISOLATED, DEPRECATE=>DEPRECATED, ARCHIVE=>ARCHIVED
- DEPRECATED 支持回退转换：DEPRECATED->ACTIVATE->ACTIVE
- RegistryIndex 搜索结果按质量降序、风险升序排列：两个同类型条目中高优先返回
- 反馈推荐计算：净评分 > 0.3 且信号数 >= 3 时为 "promote"，净评分 < -0.3 时为 "review_or_deprecate"，修正信号平均 > 0.3 时为 "revise"

## 5. Integration Tests

测试文件: `tests/test_phase12_operating_system.py`（Phase12CLITest 类）

- `test_lifecycle_show_cli`：CLI lifecycle show --asset-id a1 --current-state draft 返回 JSON 含 available_actions
- `test_lifecycle_apply_cli`：CLI lifecycle apply --action activate --from-state draft 返回 action="activate" 且 to_state="active"
- `test_lifecycle_history_cli`：apply 后 history 返回 1 条记录
- `test_registry_add_and_search_cli`：CLI registry add + search --name Test 返回 >=1 条匹配
- `test_registry_list_cli`：add 后 list 返回 1 条记录
- `test_feedback_record_and_list_cli`：CLI feedback record + list 返回 >=1 条信号
- `test_feedback_recommend_cli`：CLI feedback recommend 返回 JSON 含 recommendation 字段

## 6. Acceptance Tests

验收方式：运行完整测试套件

```bash
PYTHONPATH=src python3 -m pytest tests/test_phase12_operating_system.py -v
```

预期：全部 25 条测试通过（Phase12LifecycleTest: 9, Phase12RegistryTest: 4, Phase12FeedbackTest: 5, Phase12CLITest: 7）。

## 7. Regression Risks

- 状态转换表 TRANSITIONS 修改导致状态机行为异常：运行全套 LifecycleTest 验证
- LifecycleLedger JSONL 文件格式变更导致历史数据读取失败：运行 ledger append/list 测试
- RegistryIndex 添加重复 (entry_id, source) 条目的覆盖逻辑错误导致数据丢失：运行 add+search 测试
- FeedbackLoop compute_recommendation 的决策阈值（0.3）调整影响推荐结果：运行 recommend 系列测试
- CLI 子命令参数名变更导致脚本兼容性问题：运行全部 CLI 测试验证 JSON 响应结构

## 8. Test Commands

```bash
# 运行 Phase 12 全部测试
PYTHONPATH=src python3 -m pytest tests/test_phase12_operating_system.py -v

# 仅运行单元测试（跳过 CLI 集成测试）
PYTHONPATH=src python3 -m pytest tests/test_phase12_operating_system.py -v -k "not CLITest"

# 仅运行生命周期测试
PYTHONPATH=src python3 -m pytest tests/test_phase12_operating_system.py -v -k "LifecycleTest"

# 仅运行注册中心测试
PYTHONPATH=src python3 -m pytest tests/test_phase12_operating_system.py -v -k "RegistryTest"

# 仅运行反馈闭环测试
PYTHONPATH=src python3 -m pytest tests/test_phase12_operating_system.py -v -k "FeedbackTest"

# 运行完整检查脚本
./scripts/check.sh
```
