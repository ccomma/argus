# Argus

AI 智能体能力治理操作系统 (Capability Operating System)。零外部依赖，纯 Python 标准库，JSON/JSONL 文件存储。

**一句话**: 把模糊意图转化为可执行、可验收、可复盘的 work contract；把分散的 AI 技能、规则、记忆、工作流纳入可追溯、可回滚的能力生命周期管理。

## 项目状态

12 个阶段全部完成，201 个测试通过。

## 快速开始

```bash
# 运行全部测试
python -m unittest discover tests/ -v

# 查看所有 CLI 命令
PYTHONPATH=src python -m argus.cli --help

# 起草一份工作合约
PYTHONPATH=src python -m argus.cli contract draft \
  --intent "你的模糊意图" --mode quick

# 扫描本地能力资产
PYTHONPATH=src python -m argus.cli assets scan --profile local-codex

# 启动本地 Web 工作台
PYTHONPATH=src python -m argus.cli web --store .argus

# 启动 MCP 服务器（供外部 agent 查询）
PYTHONPATH=src python -m argus.cli mcp-serve --store .argus
```

## 文档导航

本项目 `docs/` 目录按职责分层。以下几类读者建议不同阅读路径：

### 我想理解项目全貌（30 分钟）

1. **本文件**（你在看的 README）—— 项目是什么、解决什么问题
2. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) —— 完整架构文档，含 Mermaid 图表、数据流、12 阶段地图、CLI 参考
3. [`docs/roadmap/ARGUS_DEVELOPMENT_PLAN.md`](docs/roadmap/ARGUS_DEVELOPMENT_PLAN.md) —— 12 阶段路线图：每阶段目标、验收标准、前置条件

### 我想开始开发（15 分钟）

1. [`docs/context/CURRENT_HANDOFF.md`](docs/context/CURRENT_HANDOFF.md) —— 当前状态、分支、验证命令、下一步
2. [`docs/process/DEVELOPMENT_FLOW.md`](docs/process/DEVELOPMENT_FLOW.md) —— 8 步开发流程（PRD → 技术设计 → 测试计划 → 代码 → 复盘）
3. [`CLAUDE.md`](CLAUDE.md) —— 冷启动入口，指向关键流程和可用技能

### 我想了解某一阶段的设计细节

| 文档层 | 目录 | 职责 |
|--------|------|------|
| 产品需求 | [`docs/prd/`](docs/prd/) | 为什么做、给谁用、成功标准、非目标 |
| 技术设计 | [`docs/technical/`](docs/technical/) | 模块边界、数据模型、接口、存储、安全 |
| 测试计划 | [`docs/testing/`](docs/testing/) | 测试策略、fixture、回归风险、验证命令 |
| 阶段交接 | [`docs/phases/`](docs/phases/) | 阶段执行包（HANDOFF + IMPLEMENTATION_PLAN + ACCEPTANCE） |
| 架构决策 | [`docs/adr/`](docs/adr/) | 难逆转的持久决策及备选方案 |

### 我想了解领域概念

- [`docs/agents/domain.md`](docs/agents/domain.md) —— 核心概念、术语、关系

### 我想写文档或创建新阶段

- [`docs/templates/`](docs/templates/) —— PRD、技术设计、测试计划、ADR、handoff 等模板

## 文档全景图

```text
README.md                          ← 你在看（项目入口）
CLAUDE.md                           ← 冷启动入口（agent 第一读）

docs/
├── ARCHITECTURE.md                 ← 完整架构文档（含图表）
├── README.md                       ← docs/ 命名空间说明
│
├── context/
│   └── CURRENT_HANDOFF.md          ← 当前阶段、分支、下一步
│
├── process/
│   └── DEVELOPMENT_FLOW.md         ← 8 步开发流程
│
├── roadmap/
│   └── ARGUS_DEVELOPMENT_PLAN.md   ← 12 阶段路线图
│
├── prd/                            ← 阶段 1-12 产品需求文档
├── technical/                      ← 阶段 1-12 技术设计文档
├── testing/                        ← 阶段 1-12 测试计划
├── phases/                         ← 阶段 1-12 执行包
├── adr/                            ← 架构决策记录（ADR 1-4）
│
├── agents/                         ← agent 面向约定
├── templates/                      ← 可复用文档骨架
└── context/                        ← 会话入口与加载策略
```

## 代码结构

```text
src/argus/
├── contracts/              # 工作合约（起草、交付物评估、证据）
├── ledger/                 # 追加式事件账本 + 候选学习项
├── assets/                 # 能力资产扫描、清单、报告
├── capability_packs/       # 版本化能力包 + 角色组合
├── governance/             # 治理报告 + 风险分析
├── capability_resolution/  # 能力缺口匹配与解决建议
├── controlled_modification/# 受控修改、快照、diff、审计、回滚
├── adapter/                # 跨 agent 适配器（Codex、Claude）
├── mcp/                    # MCP JSON-RPC 2.0 服务器（stdio）
├── handoff/                # 角色交接记录
├── analytics/              # ROI 计算器 + 仪表盘报告
├── maintenance/            # 维护引擎（重复/冲突/未使用检测）
├── web/                    # 本地 Web 工作台（11 页）
├── strategy/               # 策略自动化引擎（11 条默认规则）
├── playbook/               # 个人剧本注册中心
├── versioning/             # 能力版本锁定
├── security/               # 提示注入 + 供应链安全扫描
├── team/                   # 团队模型、编目、策略
├── onboarding/             # 入职包生成器
├── lifecycle/              # 资产生命周期状态机（7 状态 9 操作）
├── registry/               # 多注册中心能力发现
├── feedback/               # 闭环反馈引擎（net_score 推荐）
├── application/            # 应用服务层
├── storage.py              # JSON/JSONL 存储后端
├── paths.py                # 路径约定
└── cli/                    # 命令行入口（16 个命令族）
```

## 核心约束

- **零外部依赖**：仅使用 Python 标准库
- **不可变数据模型**：frozen dataclass，追加写入
- **内容寻址 ID**：SHA-1 确定性标识
- **追加式审计**：JSONL 不可变事件流
- **运行时无关核心**：agent 适配器在边缘，核心模型不绑定特定运行时

## 为什么叫 Argus？

Argus（阿耳戈斯）是希腊神话中的百眼巨人，即使在睡眠时也能保持部分眼睛睁开持续监视。这恰好对应了本系统的核心能力：对 AI 智能体的能力资产、行为变化、学习过程和治理状态进行全方位的持续观测与管理。

## 设计原则

- 本地优先。运行时无关核心，agent 适配器在边缘。
- 工作合约不是聊天摘要，需要目标、边界、确认点和验收标准。
- 角色不是人格，是受控的工作流、提问、交付物和能力包组合。
- 优先复用已有能力，而非生成新规则或技能。
- 低风险治理工作自动化，高风险行为变更需显式确认、备份和回滚路径。
- 衡量学习是否真正改进了后续工作。
