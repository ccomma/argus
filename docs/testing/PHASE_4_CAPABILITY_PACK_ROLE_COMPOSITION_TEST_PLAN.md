# Phase 4: 能力包与角色组合 测试计划

> 上下文加载：新会话默认先读 `docs/context/CURRENT_HANDOFF.md`，再按需读取本测试计划。当前验收状态写入阶段目录的 `ACCEPTANCE.md`。

## 1. 范围

本测试计划覆盖：

- 能力包清单（capability pack manifest）创建与持久化。
- 规范内容哈希（canonical content hash）。
- 风险推断与聚合风险。
- 必需/可选完整性检查。
- 工作契约与能力包绑定。
- 角色能力包创建与检查。
- 缺失能力和重复资产的建议。
- CLI 流程。

不覆盖：

- 外部安装。
- 源资产修改。
- 远程注册表。
- 完整治理审批。
- 嵌套能力包组合。

## 2. 单元测试

- `infer_risk` 遵循确定性策略表。
- `CapabilityPackCreator` 写入稳定的版本化清单。
- `CapabilityPackChecker` 报告缺失必需资产，不修改清单。
- `CapabilityPackBindingStore` 写入具体的契约版本、包版本和哈希。
- `RolePackStore` 引用包 ID 并复用包检查。
- `CapabilityPackAdvisor` 报告缺失能力和重复资产组。

## 3. 集成测试

- CLI `packs create`、`packs inspect`、`packs check`。
- CLI `contract bind-pack`。
- CLI `roles create-pack`。
- 通过 `./scripts/check.sh` 进行完整单元发现。

## 4. 验收冒烟测试

对真实本机路径执行扫描，写入 `/private/tmp`：

```bash
PYTHONPATH=src python3 -m argus.cli assets scan --store /private/tmp/argus-phase4-closeout/.argus --profile local-codex
```

然后创建并检查一个真实的 `product-manager-pack`，创建/检查 `product-manager` 角色包，将模糊工作契约绑定到该包，运行 `packs advise`，并通过从临时清单中移除必需资产来模拟必需资产缺失漂移场景。

## 5. 回归风险

- 清单检查意外覆写已持久化文件。
- 契约绑定遗漏包版本或内容哈希。
- 角色包内联资产条目，重复包 schema。
- 风险推断变为非确定性。
- CLI JSON 输出破坏自动化。

## 6. 测试命令

```bash
PYTHONPATH=src python3 -m unittest tests.test_phase4_capability_packs
./scripts/check.sh
```
