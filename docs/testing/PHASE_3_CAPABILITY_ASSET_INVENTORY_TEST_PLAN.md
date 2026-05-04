# Phase 3: 个人本地能力资产清单 测试计划

> 上下文加载：新会话默认先读 `docs/context/CURRENT_HANDOFF.md`，再按需读取本测试计划。当前验收状态写入阶段目录的 `ACCEPTANCE.md`。

## 1. 范围

本测试计划覆盖：

- `CapabilityAsset` 模型。
- skills/plugins/MCP/rules/scripts/memory 扫描。
- 清单（inventory）持久化。
- 资产扫描报告。
- 重复提示（duplicate hints）。
- 候选学习项到资产的关联。
- 资产 CLI 流程。

不覆盖：

- 外部能力安装。
- 源资产修改。
- 团队策略。
- 完整安全扫描。

## 2. 固定样例

固定样例：

- `tests/fixtures/assets/skills/research/SKILL.md`：skill 发现。
- `tests/fixtures/assets/plugins/demo/.codex-plugin/plugin.json`：plugin manifest 发现。
- `tests/fixtures/assets/mcp.json`：MCP server 发现。
- `tests/fixtures/assets/mcp.toml`：Codex 风格 TOML MCP server 发现。
- `tests/fixtures/assets/rules/AGENTS.md`：rule 文件发现。
- `tests/fixtures/assets/scripts/repair.sh`：script 发现。
- `tests/fixtures/assets/memory/MEMORY.md`：memory 发现。

## 3. 单元测试

- `CapabilityAssetScanner`：发现六类资产。
- `CapabilityInventory`：写入和读取清单。
- `CandidateAssetLinker`：将工具陷阱（tool pitfall）学习项匹配到对应脚本。
- `CandidateAssetLinker`：不会仅凭通用能力关键词匹配资产。
- `AssetReporter`：输出重复提示。
- `AssetReporter`：输出冲突提示和风险资产。

## 4. 样例测试

- 固定资产样例扫描输出稳定的六类资产。
- 重复 skill 扫描路径只生成一个资产。
- plugin manifest 中 permissions 和 version 被保留。
- MCP config 中 command/env 转换为 process/environment 权限。
- MCP TOML config 中 command/url 转换为 process/network 权限。
- `local-codex` profile 使用相对于 home 目录的默认路径。

## 5. 集成测试

- CLI `assets scan` 写入清单。
- CLI `assets scan --profile local-codex` 使用默认本机扫描 profile。
- CLI `assets list` 输出 JSON 资产列表。
- CLI `assets report` 写入 Markdown 报告。
- CLI `assets link-learnings` 写入候选学习项到资产关联报告。

## 6. 验收测试

- 对真实本机 skill/plugin/memory 路径执行只读扫描冒烟测试。
- 检查 warnings。
- 确认源资产文件没有被修改。

## 7. 回归风险

- 扫描器扫描范围过大：用样例控制输出。
- 重复判断过度合并：仅报告潜在重复（potential duplicate），不自动合并。
- risk_score 被误解为安全结论：文档和报告保持启发式（heuristic）表述。
- CLI JSON 输出破坏自动化：CLI 测试解析 JSON。

## 8. 测试命令

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
python3 -m compileall -q src tests
git diff --check
```
