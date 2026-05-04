# Phase 12: AI Work Contract & Capability OS Technical Design

> Context loading: 新会话默认先读 `docs/context/CURRENT_HANDOFF.md`，再按需读取本技术设计。本文件回答模块、接口、数据和风险边界，不记录每日执行状态。

## 1. Overview

Phase 12 是 Argus 的能力操作系统终局阶段，新增三大基础设施：(1) 资产生命周期状态机，为每个能力资产提供严格受控的 DRAFT->ACTIVE->ARCHIVED 状态转换与完整审计追踪；(2) 多注册中心能力发现，统一索引多来源能力条目并支持多维度搜索；(3) 闭环反馈系统，收集 agent 执行信号并基于聚合分析生成 promote/revise/deprecate 推荐，实现自优化治理。

## 2. Architecture

```
lifecycle/                       registry/                        feedback/
  AssetState (enum)                RegistryEntry (frozen)           FeedbackSignal (frozen)
  LifecycleAction (enum)           ├─ entry_id, name               ├─ signal_id
  TRANSITIONS (table)              ├─ entry_type, source           ├─ source_type/id
  StateMachine                     ├─ version, description         ├─ signal_type
    ├─ can(action)                 ├─ risk_score, quality_score    ├─ target_type/id
    ├─ available_actions()         └─ tags                        ├─ strength
    └─ apply(action)             RegistryIndex                    └─ evidence
  LifecycleRecord (frozen)         ├─ entries: RegistryEntry[]   FeedbackLoop
    ├─ record_id, asset_id         ├─ registries: list[str]        ├─ record()
    ├─ action, from_state          ├─ search(name, type, tags,    ├─ list_signals()
    │  to_state                      quality, risk)               ├─ aggregate_strength()
    ├─ triggered_by, reason        ├─ add/remove/load/save        └─ compute_recommendation()
    └─ timestamp                   └─ to_dict()
  LifecycleLedger
    ├─ append(record)  → JSONL
    ├─ list_all()
    └─ for_asset(asset_id)
```

数据流：StateMachine 加固资产状态转换（7 状态 × 15 转换边），每次变更通过 LifecycleLedger 追加写入 JSONL 账本。RegistryIndex 作为统一发现层，聚合多条来源的能力条目并提供质量/风险过滤搜索。FeedbackLoop 接收 success/failure/correction 信号，通过净评分算法驱动能力资产的生命周期推荐。

## 3. Data Model

```text
# ---- Lifecycle ----
AssetState (enum):
  DRAFT → ACTIVE → DISABLED / ISOLATED / DEPRECATED → ARCHIVED → DELETED

LifecycleAction (enum):
  CREATE, ACTIVATE, DISABLE, ISOLATE, RELEASE, DEPRECATE, ARCHIVE, DELETE, ROLLBACK

TRANSITIONS: dict[AssetState, dict[LifecycleAction, AssetState]]
  DRAFT:    ACTIVATE→ACTIVE,   ARCHIVE→ARCHIVED, DELETE→DELETED
  ACTIVE:   DISABLE→DISABLED,  ISOLATE→ISOLATED, DEPRECATE→DEPRECATED, ARCHIVE→ARCHIVED
  DISABLED: ACTIVATE→ACTIVE,   ARCHIVE→ARCHIVED
  ISOLATED: RELEASE→ACTIVE,    ARCHIVE→ARCHIVED
  DEPRECATED: ACTIVATE→ACTIVE, ARCHIVE→ARCHIVED
  ARCHIVED: ACTIVATE→ACTIVE,   DELETE→DELETED
  DELETED:  (终态，无可转换边)

StateMachine (mutable)
- current: AssetState           # 追踪当前状态
- transitions: class-level TRANSITIONS 引用
+ can(action) → bool            # 合法性检查
+ available_actions() → list    # 列出可用操作
+ apply(action) → AssetState    # 执行转换（非法抛出 ValueError）

LifecycleRecord (frozen dataclass)
- record_id: str                # SHA-1 前 12 位（asset_id + action + timestamp）
- asset_id: str                 # 目标资产 ID
- asset_type: str               # 资产类型
- action: LifecycleAction       # 执行的操作
- from_state: AssetState        # 转换前状态
- to_state: AssetState          # 转换后状态
- triggered_by: str             # 触发者（user/system/argus-cli）
- reason: str                   # 变更原因
- evidence: dict[str, Any]      # 支持证据
- timestamp: int                # Unixtime

# ---- Registry ----
RegistryEntry (frozen dataclass)
- entry_id: str                 # 条目唯一 ID
- name: str                     # 能力名称
- entry_type: str               # 类型（skill/plugin/mcp/rule/script）
- source: str                   # 来源 URL 或注册中心标识
- version: str                  # 版本，默认 "latest"
- description: str              # 描述
- author: str                   # 作者
- risk_score: float             # 风险评分，默认 0.0
- quality_score: float          # 质量评分，默认 0.5
- download_count: int           # 下载次数
- tags: list[str]               # 标签

RegistryIndex (mutable dataclass)
- entries: list[RegistryEntry]  # 能力条目集
- registries: list[str]         # 关联注册中心列表，默认 ["local"]
- last_updated: int             # 最后更新时间
+ search(name, entry_type, tags, min_quality, max_risk) → list[RegistryEntry]
  排序: 质量降序优先，相同质量按风险升序
  tags 匹配: OR 逻辑（任一条目标签命中即匹配）
+ add(entry)                    # 同 (entry_id, source) 原地替换
+ remove(entry_id, source)

# ---- Feedback ----
FeedbackSignal (frozen dataclass)
- signal_id: str                # SHA-1 前 12 位
- source_type: str              # 信号来源类型（contract/evaluation/agent）
- source_id: str                # 来源标识
- signal_type: str              # success / failure / correction
- target_type: str              # 目标类型（capability/pack/role）
- target_id: str                # 目标标识
- strength: float               # 信号强度
- evidence: dict[str, Any]      # 证据
```

## 4. Interfaces

### CLI

```text
argus lifecycle show|apply|history
  show:    --asset-id --asset-type <capability> --current-state <draft>
           输出: { asset_id, current_state, available_actions }
  apply:   --asset-id --asset-type --action --from-state [--triggered-by] [--reason]
           执行状态转换并追加到生命周期账本
  history: --asset-id (列出该资产所有状态变更记录)

argus registry search|add|list
  search:  --name <str> --type <str> --tag <tag> [--min-quality 0.0] [--max-risk 1.0]
           name: 子串匹配（大小写不敏感）
           type: 精确匹配
           tags: OR 逻辑，任一匹配即返回
  add:     --entry-id --name --type --source [--version] [--description]
           [--quality-score 0.5] [--risk-score 0.0]
  list:    列出所有注册条目

argus feedback record|list|recommend
  record:   --source-type --source-id --signal-type --target-type
            --target-id --strength <float>
  list:     [--target-type] [--target-id] [--signal-type]
  recommend: --target-type --target-id
            输出: { promote_strength, demote_strength, revise_strength,
                   net_score, total_signals, recommendation }
```

### Python API

```python
from argus.lifecycle import (
    AssetState, LifecycleAction, StateMachine, LifecycleRecord, LifecycleLedger, state_machine_for
)
from argus.registry import RegistryEntry, RegistryIndex
from argus.feedback import FeedbackLoop

# 生命周期
sm = state_machine_for("draft")        # 从 current_state 字符串创建状态机
assert sm.can(LifecycleAction.ACTIVATE) == True
new_state = sm.apply(LifecycleAction.ACTIVATE)  # → AssetState.ACTIVE
record = LifecycleRecord.create(
    asset_id="my-skill", asset_type="skill",
    action=LifecycleAction.ACTIVATE,
    from_state=AssetState.DRAFT, to_state=new_state,
    triggered_by="argus-cli", reason="Ready for production"
)
ledger = LifecycleLedger(path); ledger.append(record)
ledger.for_asset("my-skill")           # 按资产筛选历史

# 非法转换处理
try:
    sm.apply(LifecycleAction.DELETE)   # DRAFT→DELETE 在转换表中存在，可执行
except ValueError as e:
    # 仅当不可达时抛出
    pass

# 注册中心
idx = RegistryIndex.load(path)
entry = RegistryEntry(entry_id="gh-skill-1", name="my-skill",
                      entry_type="skill", source="github.com/org/repo",
                      quality_score=0.8, risk_score=0.1, tags=["python"])
idx.add(entry)
results = idx.search(name="skill", entry_type="skill", min_quality=0.5, max_risk=0.3)
idx.save(path)

# 反馈闭环
loop = FeedbackLoop(Path("feedback"))
signal = loop.record(source_type="evaluation", source_id="eval-1",
                     signal_type="success", target_type="capability",
                     target_id="my-skill", strength=0.9)
avg = loop.aggregate_strength("capability", "my-skill", "success")  # → 0.9
rec = loop.compute_recommendation("capability", "my-skill")
# rec["recommendation"] → "observe" (信号数不足 3) 或 "promote" / "review_or_deprecate" / "revise"
```

## 5. Storage

| 数据 | 存储路径 | 格式 | 读写特征 |
|------|---------|------|--------|
| 生命周期账本 | `<store>/lifecycle/ledger.jsonl` | JSONL | 追加写入（append-only） |
| 注册索引 | `<store>/registry/index.json` | JSON | 覆盖写入（save 时全量替换） |
| 反馈信号 | `<store>/feedback/{signal_id}.json` | JSON | 每个信号独立文件 |

LifecycleLedger 采用与 EventLedger 一致的追加写入 JSONL 模式，保证原子性和审计完整性。RegistryIndex 支持 deltas 方式的 add/remove（内存操作）后调用 save() 全量写入。FeedbackLoop 每个信号独立存储为 JSON 文件，便于按 signal_id 检索和去重。

## 6. Governance and Security

- **状态转换约束**：StateMachine 通过硬编码的 TRANSITIONS 表严格控制状态转换，任何非法操作抛出 ValueError。DELETED 状态为终态，无可转换边（不可逆删除）。
- **审计追踪**：LifecycleLedger.append() 为每条状态变更生成 LifecycleRecord（含 triggered_by、reason、evidence），保留完整操作者身份和操作意图。JSONL 追加写入保证不可篡改（append-only）。
- **异常回退**：state_machine_for() 对非法状态字符串回退为 DRAFT（保守安全默认）。非法 LifecycleAction 在 sm.apply() 时抛出 ValueError，不下沉到账本。
- **注册安全**：RegistryIndex.search() 按质量和风险过滤，默认 min_quality=0.0、max_risk=1.0 不做限制。调用方应根据团队策略（Phase 11 TeamPolicy）设置合理的质量/风险阈值。
- **反馈数据隔离**：每个反馈信号独立文件存储，避免单文件损坏导致全量丢失。信号强度不受限范围，但推荐算法对净评分的阈值设定（>0.3 提升、<-0.3 弃用）为合理的启发式边界。

## 7. Failure Modes

- **状态机非法操作**：sm.apply() 对不在转换表中的 (current, action) 组合抛出 ValueError，调用方必须捕获。CLI handler 捕获后返回 `{"error": "Cannot X from Y"}` 和退出码 1。
- **状态字符串非法**：state_machine_for("invalid") 回退为 DRAFT 状态创建状态机，不会崩溃，但可能产生非预期行为（调用方应预先校验状态有效性）。
- **注册索引文件缺失**：RegistryIndex.load() 返回空实例（entries=[]，registries=["local"]），搜索返回空列表。
- **反馈信号目录不存在**：FeedbackLoop.record() 自动创建目录（mkdir parents），list_signals() 返回空列表。
- **净评分极端值**：promote/demote/revise 强度值不受 clamp 限制，但推荐逻辑仅依赖阈值比较，极端值不影响逻辑正确性。
- **状态转换并发冲突**：当前无并发控制机制（单进程文件系统架构），多个 CLI 实例同时 apply 可能导致状态不一致（最后一次写入覆盖前一次）。

## 8. Test Strategy

- **Unit Tests**：StateMachine 每条合法转换边（15 条）和非法转换边界。state_machine_for 非法输入回退行为。RegistryIndex.search() 各过滤维度组合和排序验证。FeedbackLoop.aggregate_strength() 空/单/多信号场景。compute_recommendation() 四种推荐结果的阈值边界和信号数条件。
- **Fixture Tests**：固定 JSONL fixture 文件测试 LifecycleLedger.list_all/for_asset 反序列化完整性。固定 registry index JSON 测试 search 过滤器精度。
- **Integration Tests**：CLI lifecycle apply→history 完整链路（执行转换→账本写入→历史查询一致性）。CLI feedback record→list→recommend 端到端（记录信号→筛选查询→推荐计算）。
- **Acceptance Tests**：完整能力资产生命周期：DRAFT→ACTIVATE→DEPRECATE→ARCHIVE→DELETE 五步路径，每步校验状态转换合法性、账本记录完整性和返回的 to_state 正确性。

## 9. Compatibility

- **与 Phase 7 Controlled Modification 的关系**：生命周期状态机和 Phase 7 的快照/回滚机制互补——Phase 7 管理文件层面变更，Phase 12 管理逻辑状态转换。两者通过 asset_id 关联。
- **与 Phase 8 MCP Server 的关系**：RegistryIndex 可作为 MCP 工具的后端数据源，提供能力发现能力。AssetState 的状态信息可暴露给 Agent 用于运行时决策。
- **与 Phase 11 Team 策略的关系**：注册中心搜索的质量/风险过滤参数应与 TeamPolicy 的 allowed_sources/blocked_sources 联动，当前由调用方手动协调。
- **反馈信号格式稳定**：FeedbackSignal.to_dict() 和 from_dict（反序列化时直接字段构造）格式稳定，`strength` 为 float 无损序列化。

## 10. Open Questions

- 生命周期状态机当前为内存对象（非持久化），并发场景下多个 CLI 实例操作同一资产可能出现竞争条件。是否需要引入基于文件锁的并发控制（如 advisory lock）。
- `TRANSITIONS` 表当前硬编码，是否需要支持可插拔的转换表（如通过 JSON 配置文件自定义特定资产类型的转换规则）。
- FeedbackLoop 的推荐阈值（net_score > 0.3 提升、signal_count >= 3 才有资格提升）是否需要可配置，而非硬编码。
- 注册中心的 `registries` 字段当前仅标记为 `["local"]`，未来对接外部注册中心（如 Skillsmith API）时的同步/缓存策略。
- LifecycleAction.ROLLBACK 枚举存在但 TRANSITIONS 表未定义其转换（类似 Phase 7 的快照回滚概念），是否需要在此状态机中补全 ROLLBACK 转换边。
