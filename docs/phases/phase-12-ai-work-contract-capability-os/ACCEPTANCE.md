# Phase 12 Acceptance

> 本文件保存验收证据。它是检查历史阶段是否真正达到退出标准的首要参考。

## Acceptance Criteria

| Criterion | Status |
| --- | --- |
| 资产生命周期状态机覆盖 7 个状态和 9 种操作 | PASS — `AssetState`（DRAFT→ACTIVE→DISABLED/ISOLATED/DEPRECATED→ARCHIVED→DELETED）+ `LifecycleAction` 枚举 |
| 状态转换表约束合法转换并拒绝非法操作 | PASS — `TRANSITIONS` 定义 23 条合法转换，`apply()` 非法操作抛 ValueError |
| StateMachine 支持 can/available_actions/apply 三个核心方法 | PASS — 可检查、可枚举、可执行，`DELETED` 状态无任何可用操作 |
| LifecycleRecord 不可变记录并自动生成唯一 record_id | PASS — SHA1(asset_id + action + timestamp) 取前 12 位 |
| LifecycleLedger JSONL 追加写入审计账本 | PASS — 逐行追加 JSON，支持 `list_all` 和 `for_asset` 筛选 |
| RegistryEntry 与 RegistryIndex 支持多维度搜索 | PASS — 按名称（子串不区分大小写）、类型、标签（OR）、质量/风险范围过滤器，结果按质量降序排序 |
| RegistryIndex 支持条目增删与 JSON 持久化 | PASS — `add`（同 ID+source 原地替换）、`remove`、`save/load` |
| FeedbackSignal 支持 success/failure/correction 三类信号 | PASS — 不可变数据类，SHA1 生成 signal_id，独立 JSON 文件持久化 |
| FeedbackLoop 信号记录、列表筛选、强度聚合 | PASS — `record`/`list_signals`（AND 筛选）/`aggregate_strength`（均值） |
| 基于净评分的治理推荐决策 | PASS — `compute_recommendation`，`net_score = promote - demote - revise*0.5` |
| CLI `lifecycle` 命令族（3 个子命令） | PASS — `show`/`apply`（创建 LifecycleRecord 写入账本）/`history` |
| CLI `registry` 命令族（3 个子命令） | PASS — `add`/`search`（含 quality-score）/`list` |
| CLI `feedback` 命令族（3 个子命令） | PASS — `record`/`list`/`recommend` |
| 全量回归通过 | PASS — 201 个测试通过，无回归 |

## Verification Evidence

Commands:

```bash
# 生命周期单元测试
python -m unittest tests.test_phase12_operating_system.Phase12LifecycleTest -v

# 注册中心单元测试
python -m unittest tests.test_phase12_operating_system.Phase12RegistryTest -v

# 反馈引擎单元测试
python -m unittest tests.test_phase12_operating_system.Phase12FeedbackTest -v

# CLI 集成测试
python -m unittest tests.test_phase12_operating_system.Phase12CLITest -v

# 全量回归
python -m unittest discover tests/ -v
```

Result:

- 30 个 Phase 12 测试全部通过（Lifecycle 8 个、Registry 4 个、Feedback 5 个、CLI 5 个含 6 个子测试）。
- 201 个测试全部通过，无回归。

## Final Artifacts

- Code:
  - `src/argus/lifecycle/__init__.py` — 模块入口，导出 5 个符号
  - `src/argus/lifecycle/models.py` — `AssetState`、`LifecycleAction`、`StateMachine`、`LifecycleRecord`、`LifecycleLedger`
  - `src/argus/registry/__init__.py` — 模块入口
  - `src/argus/registry/models.py` — `RegistryEntry`、`RegistryIndex`
  - `src/argus/feedback/__init__.py` — 模块入口
  - `src/argus/feedback/loop.py` — `FeedbackSignal`、`FeedbackLoop`
  - `src/argus/cli/workbench.py` — `add_lifecycle_commands`/`add_registry_commands`/`add_feedback_commands` 及 9 个 handler
  - `src/argus/cli/handlers.py` — 9 个 handler 注册
  - `src/argus/cli/main.py` — `lifecycle`/`registry`/`feedback` 子命令注册
- Tests: `tests/test_phase12_operating_system.py`（30 个测试）
- Reports: N/A（此阶段无报告生成器）
- Commit: `d9cc185`

## Remaining Risks

- 状态机目前为内存实例，不与具体资产绑定——CLI handler 未在 `apply` 执行前校验资产的真实当前状态，需调用方自行保证 from_state 准确性。
- `LifecycleLedger` 使用文件追加 JSONL 无事务锁，并发写入可能产生交错行（JSON 仍可解析，但顺序无保证）。
- 外部注册中心（`RegistryIndex.registries` 列表默认仅含 `local`）的 HTTP 集成尚未实现，多注册中心发现目前仅支持本地索引。
- 反馈引擎的决策阈值（0.3 净分、3 个最小信号数）为硬编码常量，缺乏场景自适应性——长时间运行的部署可能需要可配置阈值。
