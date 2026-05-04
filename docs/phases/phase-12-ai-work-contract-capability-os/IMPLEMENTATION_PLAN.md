# Phase 12 Implementation Plan

> 这是阶段任务跟踪表，应保持简短和可操作；产品推理属于 PRD，架构决策属于技术设计，证明属于 `ACCEPTANCE.md`。

## Goal

构建能力操作系统核心：资产全生命周期状态机（7 状态 / 9 操作）、多注册中心能力发现（带多维度搜索）和闭环反馈自优化引擎（基于净评分的推荐决策）。

## Milestones

### 1. 资产生命周期状态机

Status: done

Tasks:

- 实现 `AssetState` 枚举（DRAFT/ACTIVE/DISABLED/ISOLATED/DEPRECATED/ARCHIVED/DELETED）
- 实现 `LifecycleAction` 枚举（CREATE/ACTIVATE/DISABLE/ISOLATE/RELEASE/DEPRECATE/ARCHIVE/DELETE/ROLLBACK）
- 实现 `TRANSITIONS` 状态转换表（两层 dict，外层当前状态，内层操作到目标状态）
- 实现 `StateMachine` 类：`can(action)` 检查是否可执行、`available_actions()` 列出可用操作、`apply(action)` 执行转换（非法操作抛 ValueError）
- 实现 `state_machine_for(status: str)` 工厂函数（非法状态值回退 DRAFT）
- 实现 `LifecycleRecord` 不可变记录（SHA1 生成 record_id，9 个字段）
- 实现 `LifecycleRecord.create()` 工厂方法（自动填充 record_id 和时间戳）
- 实现 `LifecycleLedger` JSONL 追加写入审计账本：`append`/`list_all`/`for_asset`

### 2. 多注册中心能力发现

Status: done

Tasks:

- 实现 `RegistryEntry` 不可变数据类（11 个字段：entry_id/name/entry_type/source/version/description/author/risk_score/quality_score/download_count/tags）
- 实现 `RegistryIndex` 索引类（entries/registries/last_updated）
- 实现 `search(name, entry_type, tags, min_quality, max_risk)` 多维度搜索——子串匹配、类型精确匹配、标签 OR、质量/风险过滤，结果按质量降序/风险升序排列
- 实现 `add(entry)` 添加或更新条目（同一 entry_id+source 原地替换）
- 实现 `remove(entry_id, source)` 按 ID 移除（可选 source 精确匹配）
- 实现 `save/load` JSON 持久化

### 3. 闭环反馈自优化引擎

Status: done

Tasks:

- 实现 `FeedbackSignal` 不可变数据类（7 个字段：signal_id/source_type/source_id/signal_type/target_type/target_id/strength/evidence）
- 实现 `FeedbackLoop` 管理器（store_dir 为信号文件目录）
- 实现 `record()` 记录反馈信号：SHA1 生成 signal_id，持久化为独立 JSON 文件
- 实现 `list_signals(target_type, target_id, signal_type)` 多条件 AND 筛选
- 实现 `aggregate_strength(target_type, target_id, signal_type)` 平均强度计算（无信号返回 0.0）
- 实现 `compute_recommendation(target_type, target_id)` 核心决策：
  - 聚合 success/failure/correction 三类信号，计算 `net_score = promote - demote - revise*0.5`
  - 决策阈值：`net_score > 0.3 且信号 >= 3` → promote；`net_score < -0.3` → review_or_deprecate；`revise > 0.3` → revise；其他 → observe

### 4. CLI 命令

Status: done

Tasks:

- 实现 `lifecycle show` — 展示资产的当前状态和可用操作列表
- 实现 `lifecycle apply` — 执行一次状态转�换，记录到 LifecycleLedger
- 实现 `lifecycle history` — 按 asset_id 查询状态变更历史
- 实现 `registry add` — 向本地注册中心索引添加条目
- 实现 `registry search` — 按名称/类型/质量/风险搜索条目
- 实现 `registry list` — 列出所有已注册条目
- 实现 `feedback record` — 记录一条反馈信号
- 实现 `feedback list` — 列出所有反馈信号
- 实现 `feedback recommend` — 为指定目标计算治理推荐
- 在 `main.py` 注册 `lifecycle`/`registry`/`feedback` 子命令解析器
- 在 `handlers.py` 注册 9 个 handler 函数

### 5. 测试

Status: done

Tasks:

- `Phase12LifecycleTest` — 8 个测试：默认转换、apply 执行、非法转换抛异常、可用操作列表、ISOLATED→RELEASE 流程、DELETED 无转换、状态字符串工厂、LifecycleLedger 追加/列表/按资产筛选
- `Phase12RegistryTest` — 4 个测试：条目序列化往返、多维度搜索、条目移除、索引持久化
- `Phase12FeedbackTest` — 5 个测试：信号记录、列表与筛选、聚合强度计算、promote 推荐判断、空信号 observe 回退
- `Phase12CLITest` — 5 个测试：生命周期 CLI、生命周期应用 CLI、生命周期历史 CLI、注册中心 CLI、反馈 CLI
- 全量回归：201 个测试通过

## Verification Commands

```bash
# 生命周期测试
python -m unittest tests.test_phase12_operating_system.Phase12LifecycleTest -v

# 注册中心测试
python -m unittest tests.test_phase12_operating_system.Phase12RegistryTest -v

# 反馈引擎测试
python -m unittest tests.test_phase12_operating_system.Phase12FeedbackTest -v

# CLI 集成测试
python -m unittest tests.test_phase12_operating_system.Phase12CLITest -v

# 全量回归
python -m unittest discover tests/ -v

# CLI 冒烟测试
python -m argus lifecycle show --store /tmp/.argus --asset-id smoke --current-state draft
python -m argus registry add --store /tmp/.argus --entry-id e1 --name "Smoke" --type skill --source local
python -m argus feedback recommend --store /tmp/.argus --target-type role --target-id r1
```

## Closeout Checklist

- [x] Implementation matches PRD and technical design.
- [x] Relevant tests pass（30 个 Phase 12 测试全部通过）。
- [x] Smoke commands pass or documented as not applicable.
- [x] `ACCEPTANCE.md` records actual evidence.
- [x] Phase `HANDOFF.md` is updated for future readers.
- [x] `docs/context/CURRENT_HANDOFF.md` points to the next phase or next task.
