# Argus 开发流程

本文定义 Argus 从长期设计记忆到阶段开发、测试、复盘的标准流程。它的目标是让每次推进都可追踪、可验证，并避免把产品判断、技术设计和任务执行混在一个文档里。

Argus 从 Phase 0 起采用“短 handoff 驱动 + 长文档按需加载”的开发方式：长期文档负责方向，阶段包保存执行与证据，新会话优先读取 handoff，而不是每次完整加载所有设计材料。

## 1. 文档职责边界

| 文档 | 读者 | 负责什么 | 不负责什么 |
| --- | --- | --- | --- |
| `DESIGN.md` | 项目维护者、未来 agent | 长期定位、产品北极星、原则、非目标、架构闭环 | sprint 任务、具体 API 细节、短期实现排期 |
| `CONTEXT.md` | 开发者、agent、未来架构审查 | 领域语言、核心概念、概念关系、歧义澄清 | 产品定位、阶段状态、任务管理 |
| `docs/roadmap/ARGUS_DEVELOPMENT_PLAN.md` | 维护者、开发者、agent | 阶段路线、阶段目标、验收标准、退出条件 | 每个阶段的详细需求和代码设计 |
| `docs/prd/` | 产品和开发协作者 | 阶段需求、用户价值、成功标准、非目标 | 模块实现、存储细节、测试代码 |
| `docs/technical/` | 开发者、agent | 数据模型、模块边界、接口、存储、失败模式、安全边界 | 产品愿景和商业判断 |
| `docs/testing/` | 开发者、测试者、agent | 测试策略、fixture、验收清单、回归记录 | 产品路线和架构原则 |
| `docs/adr/` | 维护者、未来 agent | 关键技术/产品决策及原因 | 临时想法和已废弃任务清单 |
| `docs/phases/` | 当前阶段开发者、agent | 当前阶段执行包、handoff、实现计划、验收清单 | 长期产品判断 |
| `docs/context/CURRENT_HANDOFF.md` | 新会话、未来 agent | 当前阶段最小必要上下文、分支状态、验证命令、禁止事项、下一步 | 完整设计历史、详细实现说明 |

`docs/` 是共享命名空间，不属于某一个 agent、skill 或工具。写入前先按文档职责判断所有权：如果已有文档拥有该主题，就引用或补索引；只有没有清晰所有者时，才创建新文档或扩展目录。

## 2. 上下文加载协议

新会话或新 agent 承接开发时，按下面顺序加载：

1. `README.md`：了解公开项目定位和基本命令。
2. `docs/context/CURRENT_HANDOFF.md`：了解当前阶段、当前分支、已完成内容、下一步、不要碰什么、验证命令。
3. 当前阶段 `docs/phases/<phase>/HANDOFF.md`。
4. 当前任务需要的代码和测试。
5. 当前任务需要领域术语、概念关系或历史决策时，读取 `CONTEXT.md` 或对应 ADR。
6. 只有当前 handoff 无法回答产品、架构或测试边界时，才读取对应 PRD、技术设计、测试计划、roadmap 或 `DESIGN.md`。

上下文预算原则：

- 默认不完整加载 `DESIGN.md`。
- 默认不完整加载 roadmap。
- 默认不完整加载所有历史 PRD、技术设计和测试计划。
- 当前阶段 handoff 控制在 100-200 行左右。
- 当前阶段实现计划只记录可执行任务，不重复长期背景。
- 阶段结束后，把实际状态写回 handoff 和阶段验收文件。

## 3. 标准推进流程

### Step 1：更新设计记忆

当出现新的长期判断时，先判断是否应该进入 `DESIGN.md`。

适合写入：

- 产品定位变化。
- 不可妥协原则变化。
- 核心架构闭环变化。
- 长期非目标变化。

不适合写入：

- 某个阶段的任务列表。
- 某个 CLI 参数细节。
- 某次测试失败记录。

### Step 2：更新完整路线图

当阶段边界、顺序、验收标准或退出条件变化时，更新 `docs/roadmap/ARGUS_DEVELOPMENT_PLAN.md`。

路线图每个阶段至少包含：

- 目标。
- 核心能力。
- 输入。
- 输出。
- 验收标准。
- 退出条件。
- 下一阶段前置条件。

### Step 2.5：更新领域语言

当出现新的领域概念、概念关系或术语歧义时，更新 `CONTEXT.md`。

适合写入：

- 工作契约、能力资产、候选学习等领域概念的定义变化。
- 两个概念之间的关系变化。
- 反复出现的模糊词被明确成一个规范术语。

不适合写入：

- 通用编程概念。
- 某个函数、类或 CLI 参数的实现细节。
- 产品定位、阶段计划或验收证据。

### Step 3：创建阶段执行包

每进入一个阶段，先创建阶段分支：

```bash
git checkout main
git pull origin main
git checkout -b phase<NN>
```

分支命名遵循项目约定，如 `phase6`、`phase-06-<slug>`。如果当前工作树有未提交变更（如跨阶段的代码重构），从当前状态创建分支并在 handoff 中注明 base-branch 差异。

然后创建阶段执行包：

```text
docs/phases/phase-XX-<slug>/HANDOFF.md
docs/phases/phase-XX-<slug>/IMPLEMENTATION_PLAN.md
docs/phases/phase-XX-<slug>/ACCEPTANCE.md
```

其中 `HANDOFF.md` 是会话入口，`IMPLEMENTATION_PLAN.md` 是当前开发任务拆分，`ACCEPTANCE.md` 是阶段验收清单。

阶段包和阶段分支必须在阶段实现开始前存在。即使 Phase 1 / Phase 2 这种早期阶段已经完成，也要保留对应阶段包和验收证据，让未来 agent 能看到该阶段从一开始就按短 handoff 驱动方式推进。

### Step 4：编写阶段 PRD

每进入一个阶段，先在 `docs/prd/` 新建阶段 PRD。

PRD 只回答：

- 为什么做。
- 给谁用。
- 当前痛点是什么。
- 这个阶段怎样算成功。
- 明确不做什么。

PRD 不写内部模块拆分和代码结构。

### Step 5：编写阶段技术设计

PRD 稳定后，在 `docs/technical/` 新建技术设计。

技术设计回答：

- 模块边界。
- 数据模型。
- CLI / API / 文件接口。
- 数据流。
- 存储选择。
- 错误处理。
- 安全与治理边界。
- 测试策略。

如果出现影响长期方向的技术决策，同时补充 ADR。ADR 只用于难逆转、反直觉、且来自真实权衡的决策；临时取舍写入阶段 handoff 或技术设计即可。

### Step 6：拆开发任务

技术设计稳定后，再拆开发任务。

每个任务必须满足：

- 能独立实现。
- 能独立测试。
- 有明确输入输出。
- 有最小验证命令或验收方法。
- 不要求实现者重新决定产品边界。

### Step 7：开发与测试

每个阶段优先做最小可验证闭环。

推荐顺序：

1. 写 fixture 或最小样例。
2. 写核心数据模型测试。
3. 实现最小行为。
4. 跑最小相关测试。
5. 加集成测试。
6. 生成阶段报告或 CLI 输出。
7. 代码重构：按职责拆分模块，消除重复，精简代码。重构后重新跑全部测试确认无回归。
8. 做人工验收。

### Step 8：阶段复盘

阶段结束时必须回看：

- 全部测试通过，无回归。
- roadmap 是否需要调整。
- `DESIGN.md` 是否有新的长期判断。
- PRD 的成功标准是否达成。
- 技术设计有哪些偏差。
- 测试覆盖哪些风险，哪些仍未覆盖。
- 下一阶段前置条件是否满足。
- `docs/context/CURRENT_HANDOFF.md` 是否已更新到当前阶段关闭状态并指向下一阶段。
- 当前阶段 `HANDOFF.md` 是否移除了过期的待办。
- 当前阶段 `ACCEPTANCE.md` 是否记录了最新验证命令、结果、风险和最终提交。
- 当前阶段 `IMPLEMENTATION_PLAN.md` 是否标记为已完成。
- 代码重构是否完成，模块职责是否清晰。

确认上述项后，合入 main 并推送：

```bash
git checkout main
git merge phase<NN> --no-edit
git push origin main
git push origin phase<NN>
```

阶段分支保留不删除并推送至远端，以备追溯。

## 4. 阶段文档命名约定

阶段执行包：

```text
docs/phases/phase-03-capability-asset-inventory/HANDOFF.md
docs/phases/phase-03-capability-asset-inventory/IMPLEMENTATION_PLAN.md
docs/phases/phase-03-capability-asset-inventory/ACCEPTANCE.md
```

PRD：

```text
docs/prd/phase-01-codex-event-ledger-prd.md
docs/prd/phase-02-capability-asset-inventory-prd.md
```

技术设计：

```text
docs/technical/phase-01-codex-event-ledger-technical-design.md
docs/technical/phase-02-capability-asset-inventory-technical-design.md
```

测试计划：

```text
docs/testing/phase-01-codex-event-ledger-test-plan.md
docs/testing/phase-02-capability-asset-inventory-test-plan.md
```

ADR：

```text
docs/adr/ADR-0001-storage-choice.md
docs/adr/ADR-0002-event-schema-boundary.md
```

## 5. 开发节奏建议

每个阶段按小闭环推进：

1. PRD 确认。
2. 技术设计确认。
3. 测试计划确认。
4. 实现最小闭环。
5. 用 fixture 验证稳定输出。
6. 用真实样例验证价值。
7. 阶段复盘。

不要在 PRD 未稳定时提前实现复杂架构；也不要在还没有真实样例时过度设计平台能力。

## 6. Definition of Done

一个阶段完成必须满足：

- 阶段 PRD、技术设计和测试计划存在且与实现一致。
- 相关测试通过，或失败原因有明确记录。
- 阶段验收标准逐项确认。
- 没有未记录的持久行为变更。
- roadmap 已根据实际结果更新。
- 新的长期判断已回写 `DESIGN.md` 或记录为 ADR。
- 新的领域语言或术语歧义已回写 `CONTEXT.md`。
- `docs/context/CURRENT_HANDOFF.md` 已更新到下一阶段入口。
- 当前阶段 `HANDOFF.md`、`IMPLEMENTATION_PLAN.md` 和 `ACCEPTANCE.md` 已更新到最终状态。

## 7. 文档更新触发规则

不要每次开发都全量更新所有文档。按触发条件更新：

- 产品定位、目标用户、长期边界变化：更新 `DESIGN.md`。
- 领域术语、概念关系或歧义变化：更新 `CONTEXT.md`。
- 阶段顺序、验收标准、退出条件变化：更新 roadmap。
- 当前阶段目标、下一步、验证命令或分支状态变化：更新 `docs/context/CURRENT_HANDOFF.md` 和当前阶段 `HANDOFF.md`。
- 阶段任务拆分或状态变化：更新当前阶段 `IMPLEMENTATION_PLAN.md`。
- 阶段完成、测试证据、剩余风险变化：更新当前阶段 `ACCEPTANCE.md`。
- 产品需求变化：更新对应 PRD。
- 模块边界、数据模型、接口或风险策略变化：更新对应技术设计。
- 测试策略、fixture 或验收方法变化：更新对应测试计划。
- 影响多个阶段且难逆转、反直觉、有真实权衡的持久决策：新增或更新 ADR。
