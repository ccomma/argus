# Phase 3: 个人本地能力资产清单 技术设计

> 上下文加载：新会话默认先读 `docs/context/CURRENT_HANDOFF.md`，再按需读取本技术设计。本文件回答模块、接口、数据和风险边界，不记录每日执行状态。

## 1. 概述

Phase 3 在 Phase 2 学习账本之上增加能力资产清单。核心目标是将本机 AI 能力文件扫描为统一的 `CapabilityAsset`，并保持扫描过程只读。

## 2. 架构

模块边界：

- `CapabilityAsset`：统一的能力资产模型。
- `CapabilityAssetScanner`：协调各类只读扫描器。
- `AssetScanProfile`：定义可复用的扫描路径集合，例如本机 Codex profile。
- `CapabilityInventory`：读写 `.argus/assets/inventory.json`。
- `AssetReporter`：输出本地的资产扫描报告。
- `CandidateAssetLinker`：将候选学习项与本地资产进行轻量关联。
- CLI `assets` 命令组：入口和 JSON 输出。

数据流：

```text
skill/plugin/MCP/rule/script/memory paths
  -> AssetScanProfile
  -> CapabilityAssetScanner
  -> CapabilityAsset[]
  -> CapabilityInventory
  -> AssetReporter
  -> CandidateAssetLinker
```

## 3. 数据模型

```text
CapabilityAsset
- id: 稳定的资产标识符
- name: 人类可读的资产名称
- type: skill | plugin | mcp_server | rule | script | memory
- source: local_skill | codex_plugin | mcp_config | local_rule | local_script | local_memory
- version: 可发现时的版本号
- install_path: 本地路径
- agents: codex | claude | 未来的适配器名称
- scope: local | project | user | team
- permissions: filesystem | network | process | environment | 未来权限位
- risk_score: 0-1 启发式风险评分
- status: active | disabled | isolated | deprecated | archived
- metadata: 扫描器特有的精简数据
```

```text
AssetLearningLink
- learning_id: 候选学习项 ID
- asset_id: 能力资产 ID
- reason: 人类可读的匹配原因
- confidence: 0-1 启发式置信度
```

## 4. 接口

初期 CLI：

```text
argus assets scan
  --profile local-codex
  --profile-home <path>
  --skill-dir <path>
  --plugin-dir <path>
  --mcp-config <path>
  --rule-file <path>
  --script-dir <path>
  --memory-dir <path>

argus assets list
argus assets report
argus assets link-learnings
```

## 5. 存储

Phase 3 仅写入 Argus 自有的本地输出：

```text
.argus/
  assets/
    inventory.json
    reports/
      asset-scan-report.md
      candidate-asset-links.json
```

源资产文件作为只读输入。

默认扫描 profile：

```text
local-codex
- ~/.codex/skills
- ~/.agents/skills
- ~/.codex/plugins/cache
- ~/.codex/config.toml
- ~/.codex/AGENTS.md
- ~/.codex/superpowers/AGENTS.md
- ~/.codex/memories
```

MCP 配置解析支持包含 `mcpServers`、`mcp_servers` 或 `servers` 字段的 JSON 对象，以及包含 `[mcp_servers.<name>]` 段的 TOML 配置。

## 6. 治理与安全

允许的操作：

- 读取用户指定的本地路径。
- 解析本地清单和配置文件。
- 写入 Argus 资产清单和报告。
- 生成启发式风险提示和重复资产提示。
- 生成潜在冲突和高风险资产章节。

禁止的操作：

- 安装外部资产。
- 修改 skill/plugin/MCP/rule/script/memory 源文件。
- 删除或禁用资产。
- 将启发式风险评分视为安全裁决。

## 7. 失败模式

- 扫描路径不存在。
- 插件 JSON 格式无效。
- MCP JSON 配置无效。
- MCP TOML 配置无效。
- 文件不可读。
- 扫描路径过大且包含无关文件。
- 多个资产同名但语义不同。

## 8. 测试策略

- 单元测试：资产 schema、去重、风险提示、冲突提示、候选学习项到资产的关联。
- Fixture 测试：固定 skill/plugin/MCP JSON/MCP TOML/rule/script/memory fixture。
- 集成测试：CLI scan -> list -> report -> link-learnings。
- 验收测试：真实本机只读扫描冒烟测试。

## 9. 兼容性

- Phase 3 不改变 Phase 1 的契约存储。
- Phase 3 不改变 Phase 2 的账本 schema。
- 候选学习集成是只读的：它读取学习账本并写入关联报告。
- 未来 Phase 4 能力包可以消费 `CapabilityAsset`，而无需依赖扫描器内部实现。

## 10. 待解决问题

- 是否将扫描器拆分为适配器类。
- 是否支持 TOML/YAML MCP 配置。
- 是否引入项目级默认扫描 profile。
