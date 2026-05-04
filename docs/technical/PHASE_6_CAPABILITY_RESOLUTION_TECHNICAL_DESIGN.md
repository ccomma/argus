# Phase 6: Capability Resolution Technical Design

> Context loading: 新会话默认先读 `docs/context/CURRENT_HANDOFF.md`，再按需读取本技术设计。本文件回答模块、接口、数据和风险边界，不记录每日执行状态。

## 1. Overview

Phase 6 实现能力缺口解析引擎，从多源信号（学习项、能力包检查、治理发现）自动发现能力缺口，并通过四级关键词匹配算法给出处置决策（复用/配置/创建/安装）。输出能力解析报告（Markdown + JSON），供人工审阅或下游自动化消费。

## 2. Architecture

模块边界和数据流：

```
信号源                           解析引擎                      输出
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CandidateLearningItem ─────┐
  (反向学习目标)            │
                            ├──→ CapabilityResolver ──→ CapabilityResolution[]
Pack Check (缺失资产)  ─────┤         │
                            │         │ 四级匹配算法:
GovernanceFinding ──────────┘         │   1. REUSE (精确, >=50% tokens)
  (dedupe/risk/role)                  │   2. CONFIGURE (阈值 >=0.15)
                                      │   3. CREATE_LOCAL (0 < 分数 < 0.15)
                                      │   4. INSTALL_SUGGESTED (无匹配)
                                      ↓
                               ResolutionReporter ──→ .argus/governance/reports/
                                                       capability-resolution-report.md
                                                       capability-resolution-report.json
```

核心组件：
- `src/argus/capability_resolution/models.py` — 决策枚举和解析结果模型
- `src/argus/capability_resolution/resolver.py` — 解析引擎，四级匹配算法
- `src/argus/capability_resolution/reporting.py` — 双格式报告生成器
- `src/argus/application/resolution.py` — `ResolutionApplication`，聚合门面

## 3. Data Model

```text
Decision (StrEnum)
  - REUSE: 复用已有本地资产
  - CONFIGURE: 配置现有资产满足缺口
  - INSTALL_SUGGESTED: 建议安装外部能力（高风险）
  - CREATE_LOCAL: 参照相似资产创建新的本地能力
  - MERGE: 合并多个资产覆盖缺口
  - IGNORE: 忽略低优先级缺口

DECISION_RISK (dict[Decision, str])
  - REUSE/CONFIGURE/IGNORE → "low"
  - MERGE/CREATE_LOCAL → "medium"
  - INSTALL_SUGGESTED → "high"

CapabilityResolution (frozen dataclass)
  - gap_id: str                          # 缺口唯一标识
  - gap_description: str                 # 缺口描述文本
  - decision: Decision                   # 处置决策枚举
  - risk_level: str                      # low/medium/high
  - matched_local_asset_ids: list[str]   # 匹配的本地资产 ID 列表
  - external_options: list[dict[str,str]]# 外部安装候选（name/type）
  - confidence: float                    # 置信度 0.0-1.0
  - evidence: list[str]                  # 决策证据链
  - recommended_action: str              # 人类可读的建议动作
  - contract_id: str = ""                # 关联合约 ID（可选）
  - role_id: str = ""                    # 关联角色 ID（可选）
  - source: str = ""                     # 缺口来源标识

ResolutionReport (frozen dataclass)
  - markdown_path: Path                  # Markdown 报告路径
  - json_path: Path                      # JSON 报告路径
```

## 4. Interfaces

### 4.1 Python API

**CapabilityResolver** (`src/argus/capability_resolution/resolver.py`):
```python
class CapabilityResolver:
    def __init__(self, inventory: CapabilityInventory,
                 pack_store: CapabilityPackStore | None = None,
                 role_store: RolePackStore | None = None) -> None
    def resolve(self, *, gaps: list[dict], contract_id="", role_id="") -> list[CapabilityResolution]
    def resolve_from_learnings(self, learnings: list[CandidateLearningItem], ...) -> list[CapabilityResolution]
    def resolve_from_advice(self, missing_capabilities: list[str], ...) -> list[CapabilityResolution]
    def resolve_from_findings(self, findings: list[GovernanceFinding], ...) -> list[CapabilityResolution]
```

**ResolutionApplication** (`src/argus/application/resolution.py`):
```python
class ResolutionApplication:
    def resolve_all(self) -> list[CapabilityResolution]
    def write_report(self) -> ResolutionReport
```

**ResolutionReporter** (`src/argus/capability_resolution/reporting.py`):
```python
class ResolutionReporter:
    def write(self, resolutions: list[CapabilityResolution]) -> ResolutionReport
```

### 4.2 MCP 工具

通过 `MCPServer` 暴露：
- `run_resolution` — 对单个能力缺口执行解析，返回处置建议列表

## 5. Storage

- 输出目录：`.argus/governance/reports/`（复用 Phase 5 报告目录）
- 输出文件：
  - `capability-resolution-report.md`
  - `capability-resolution-report.json`
- 读取依赖：`ContractStorage`、`LearningLedger`、`CapabilityInventory`、`CapabilityPackStore`、`RolePackStore`（均为只读访问）
- 无新存储格式，无迁移需求

## 6. Governance and Security

- 解析引擎仅执行只读分析，不修改任何源数据（能力资产、合约、学习项、包清单）
- 四级决策的风险分层已内置在 `DECISION_RISK` 映射中：
  - 低风险 (REUSE, CONFIGURE, IGNORE)：无需审批，可直接建议
  - 中风险 (MERGE, CREATE_LOCAL)：建议审阅后执行
  - 高风险 (INSTALL_SUGGESTED)：需人工确认，标为 install_suggested 而非自动安装
- 去重逻辑确保同一 gap_id 只产生一条解析结果（`_deduplicate_resolutions`）

## 7. Failure Modes

- 空缺口列表：`resolve()` 返回空列表，报告显示 "No capability gaps to resolve."
- 无本地资产匹配：回退到 `INSTALL_SUGGESTED` 决策，confidence=0.3，风险等级为 high
- 资产目录不存在/为空：`_scored_matches` 和 `_find_similar` 返回空结果，最终回退到 INSTALL_SUGGESTED
- 治理报告 JSON 不合法：`_load_findings` 依赖的 JSON 文件损坏时，`json.loads` 抛出异常，由调用方处理
- 关键词提取无有效词（描述文本全部为短词）：`_extract_keywords` 返回空集合，导致所有匹配分为 0，全部进入 INSTALL_SUGGESTED
- 跨源重复缺口：`_deduplicate_resolutions` 按 gap_id 去重，保留首次出现，后续同 ID 丢弃

## 8. Test Strategy

- Unit Tests：
  - `Decision` 枚举值和 `DECISION_RISK` 映射完整性
  - `CapabilityResolution.to_dict()` / `from_dict()` 序列化往返
  - `_extract_keywords` 关键词提取（边界：空字符串、纯短词）
  - `_is_exact_match` 精确匹配逻辑（边界：50% 阈值）
  - `_keyword_overlap` 分数计算（边界：空搜索文本、上限 0.75）
  - `_deduplicate_resolutions` 去重正确性
- Fixture Tests：用 Mock `CapabilityInventory` 和预定义的 `CandidateLearningItem` 数据验证 `resolve_from_learnings`
- Integration Tests：
  - `CapabilityResolver` 四级匹配链路完整性（每种决策至少触发一次）
  - `ResolutionReporter` 输出文件存在性和内容结构
  - `ResolutionApplication.resolve_all()` 三源聚合去重
- Acceptance Tests：
  - 空白数据仓库场景（无资产、无学习项）下 resolve_all 返回空列表
  - 报告中按决策类型和风险等级分组统计正确

## 9. Compatibility

- 对已有文档无破坏性变更——仅新增解析报告文件
- `CapabilityInventory.list_assets()` 接口保持兼容
- `GovernanceFinding` 字段使用 `__dataclass_fields__` 过滤加载，兼容 JSON 中额外字段
- 依赖 Phase 1-5 的全部存储模块，需确保它们已完成初始化

## 10. Open Questions

- 关键词匹配的参数（`_CONFIGURE_THRESHOLD = 0.15`、精确匹配 50% 覆盖率）是否需要支持外部配置？
- 是否需要支持用户自定义的匹配规则/权重？当前为固定算法
- MERGE 和 IGNORE 决策在当前实现中未在四级匹配中产生——它们是为未来扩展预留的枚举值，当前仅通过手动传入 gaps 和 MERGE/IGNORE 决策组合使用
