from __future__ import annotations

"""能力资产扫描引擎模块。

提供 CapabilityAssetScanner 类——从本地文件系统自动发现和识别
各类能力资产的扫描引擎。支持六种资产类型：skill、plugin、
mcp_server、rule、script、memory。

扫描逻辑覆盖多种文件格式和目录结构，对不存在的路径静默跳过，
对解析错误收集为警告而非直接崩溃，以保证扫描的鲁棒性。
"""

import json
import tomllib
from pathlib import Path
from typing import Any, Callable

from argus.assets.models import AssetScanProfile, AssetScanResult, CapabilityAsset


class CapabilityAssetScanner:
    """能力资产扫描器。

    接收扫描配置，遍历文件系统，发现并识别各类能力资产。
    所有扫描结果最终通过 _deduplicate_assets 去重合并。
    """

    def scan_profile(self, profile: AssetScanProfile) -> AssetScanResult:
        """基于配置文件的便捷扫描方法。"""
        return self.scan(**profile.to_scan_kwargs())

    def scan(
        self,
        *,
        skill_dirs: list[str | Path] | None = None,
        plugin_dirs: list[str | Path] | None = None,
        mcp_configs: list[str | Path] | None = None,
        rule_files: list[str | Path] | None = None,
        script_dirs: list[str | Path] | None = None,
        memory_dirs: list[str | Path] | None = None,
    ) -> AssetScanResult:
        """扫描所有指定路径，发现能力资产。

        流程：
        1. 并行扫描六类资产源
        2. 每类资产使用专属的扫描函数和收集器
        3. 对扫描中的异常不中断，而是收集为警告
        4. 最终对所有资产进行去重合并

        这种"容错扫描"设计确保单个文件解析失败不会阻断整体扫描。
        """
        assets: list[CapabilityAsset] = []
        warnings: list[str] = []
        assets.extend(_collect(skill_dirs or [], _scan_skill_dir, warnings))
        assets.extend(_collect(plugin_dirs or [], _scan_plugin_dir, warnings))
        assets.extend(_collect(mcp_configs or [], _scan_mcp_config, warnings))
        assets.extend(_collect(rule_files or [], _scan_rule_file, warnings))
        assets.extend(_collect(script_dirs or [], _scan_script_dir, warnings))
        assets.extend(_collect(memory_dirs or [], _scan_memory_dir, warnings))
        return AssetScanResult(assets=_deduplicate_assets(assets), warnings=warnings)


def _collect(
    paths: list[str | Path],
    scanner: Callable[[Path], list[CapabilityAsset]],
    warnings: list[str],
) -> list[CapabilityAsset]:
    """通用资产收集器。

    对每个路径调用扫描器，捕获异常并转为警告。
    这样即使某个路径扫描失败，其余路径依然可以正常产出。
    """
    assets: list[CapabilityAsset] = []
    for path in paths:
        try:
            assets.extend(scanner(Path(path)))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            warnings.append(f"{path}: {exc}")
    return assets


def _scan_skill_dir(root: Path) -> list[CapabilityAsset]:
    """扫描技能目录。

    查找 SKILL.md 文件：如果 root 本身就是 SKILL.md，直接处理；
    否则递归查找所有名为 SKILL.md 的文件。
    """
    if not root.exists():
        return []
    skill_files = [root] if root.name == "SKILL.md" else root.rglob("SKILL.md")
    return [
        CapabilityAsset.create(
            name=skill_file.parent.name,
            type="skill",
            source="local_skill",
            install_path=skill_file.parent,
            agents=["codex"],
            scope="local",
            permissions=[],
            risk_score=0.2,  # 技能文件风险较低，因为不直接执行命令
            metadata={"manifest": str(skill_file)},
        )
        for skill_file in skill_files
        if skill_file.is_file()
    ]


def _scan_plugin_dir(root: Path) -> list[CapabilityAsset]:
    """扫描插件目录。

    查找 .codex-plugin/plugin.json 清单文件，解析插件元数据。
    有权限声明的插件风险评分更高（0.45 vs 0.25），
    因为权限意味着更大的系统访问面。
    """
    if not root.exists():
        return []
    manifests = [root] if root.name == "plugin.json" else root.rglob(".codex-plugin/plugin.json")
    assets: list[CapabilityAsset] = []
    for manifest in manifests:
        if not manifest.is_file():
            continue
        data = json.loads(manifest.read_text(encoding="utf-8"))
        plugin_root = manifest.parent.parent if manifest.parent.name == ".codex-plugin" else manifest.parent
        permissions = _plugin_permissions(data)
        assets.append(
            CapabilityAsset.create(
                name=str(data.get("name") or plugin_root.name),
                type="plugin",
                source="codex_plugin",
                version=str(data.get("version") or ""),
                install_path=plugin_root,
                agents=["codex"],
                scope="local",
                permissions=permissions,
                risk_score=0.45 if permissions else 0.25,
                metadata={"manifest": str(manifest)},
            )
        )
    return assets


def _scan_mcp_config(path: Path) -> list[CapabilityAsset]:
    """扫描 MCP 服务配置文件（TOML 或 JSON）。

    支持多种配置键名：mcpServers / mcp_servers / servers。
    根据配置中的 command/env/url 字段推断所需权限。
    有 command 或 url 的服务器风险更高（0.55 vs 0.35），
    因为它们可能执行外部命令或访问网络。
    """
    if not path.exists():
        return []
    data = _load_config(path)
    servers = data.get("mcpServers") or data.get("mcp_servers") or data.get("servers") or {}
    assets: list[CapabilityAsset] = []
    for name, config in servers.items():
        if not isinstance(config, dict):
            config = {}
        permissions = _mcp_permissions(config)
        assets.append(
            CapabilityAsset.create(
                name=str(name),
                type="mcp_server",
                source="mcp_config",
                install_path=path,
                agents=["codex"],
                scope="local",
                permissions=permissions,
                risk_score=0.55 if permissions else 0.35,
                metadata={
                    "type": config.get("type", ""),
                    "command": config.get("command", ""),
                    "args": config.get("args", []),
                    "url": config.get("url", ""),
                },
            )
        )
    return assets


def _scan_rule_file(path: Path) -> list[CapabilityAsset]:
    """扫描行为规则文件。

    根据文件名判断适用的代理：
    - AGENTS.md → codex
    - CLAUDE.md → claude
    scope 根据父目录名判断是否为项目级（project）或本地级（local）。
    """
    if not path.is_file():
        return []
    return [
        CapabilityAsset.create(
            name=path.name,
            type="rule",
            source="local_rule",
            install_path=path,
            agents=_rule_agents(path),
            scope="project" if path.parent.name else "local",
            permissions=[],
            risk_score=0.3,
        )
    ]


def _scan_script_dir(root: Path) -> list[CapabilityAsset]:
    """扫描脚本目录。

    查找 .sh/.py/.js/.ts 文件以及任何可执行文件。
    可执行文件的权限为 ["filesystem"]，风险评分取决于是否可执行：
    - 可执行: 0.5（可以直接运行，风险较高）
    - 非可执行: 0.35（仅代码文件）

    跳过隐藏文件（以 . 开头），避免扫描配置文件。
    """
    if not root.exists():
        return []
    assets: list[CapabilityAsset] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.name.startswith("."):
            continue
        if path.suffix not in {".sh", ".py", ".js", ".ts"} and not _is_executable(path):
            continue
        assets.append(
            CapabilityAsset.create(
                name=path.name,
                type="script",
                source="local_script",
                install_path=path,
                agents=[],
                scope="local",
                permissions=["filesystem"],
                risk_score=0.5 if _is_executable(path) else 0.35,
            )
        )
    return assets


def _scan_memory_dir(root: Path) -> list[CapabilityAsset]:
    """扫描记忆文件目录。

    查找 MEMORY.md 和 memory_summary.md 文件。
    记忆文件风险评分低（0.2），因为它们主要影响代理的行为偏好。
    """
    if not root.exists():
        return []
    memory_files = [path for path in root.rglob("*.md") if path.name in {"MEMORY.md", "memory_summary.md"}]
    return [
        CapabilityAsset.create(
            name=path.name,
            type="memory",
            source="local_memory",
            install_path=path,
            agents=["codex"],
            scope="local",
            permissions=[],
            risk_score=0.2,
        )
        for path in memory_files
    ]


def _deduplicate_assets(assets: list[CapabilityAsset]) -> list[CapabilityAsset]:
    """按 ID 去重资产列表。

    同时按 (type, name, install_path) 排序，确保输出稳定性。
    """
    seen = set()
    result = []
    for asset in sorted(assets, key=lambda item: (item.type, item.name, item.install_path)):
        if asset.id in seen:
            continue
        seen.add(asset.id)
        result.append(asset)
    return result


def _plugin_permissions(data: dict[str, Any]) -> list[str]:
    """从插件清单中提取权限列表。

    兼容两种格式：
    - permissions: {key: bool}（字典格式，取值为 True 的键）
    - capabilities: [string]（列表格式）
    """
    permissions = data.get("permissions") or data.get("capabilities") or []
    if isinstance(permissions, dict):
        return sorted(str(key) for key, enabled in permissions.items() if enabled)
    if isinstance(permissions, list):
        return sorted(str(permission) for permission in permissions)
    return []


def _mcp_permissions(config: dict[str, Any]) -> list[str]:
    """从 MCP 服务配置推断权限需求。

    - command → process：需要执行进程
    - env → environment：需要访问环境变量
    - url → network：需要网络访问
    """
    permissions = []
    if config.get("command"):
        permissions.append("process")
    if config.get("env"):
        permissions.append("environment")
    if config.get("url"):
        permissions.append("network")
    return permissions


def _load_config(path: Path) -> dict[str, Any]:
    """加载配置文件，自动识别 TOML 或 JSON 格式。"""
    if path.suffix == ".toml":
        with path.open("rb") as handle:
            return tomllib.load(handle)
    return json.loads(path.read_text(encoding="utf-8"))


def _rule_agents(path: Path) -> list[str]:
    """根据规则文件名推断适用的代理。"""
    if path.name == "AGENTS.md":
        return ["codex"]
    if path.name == "CLAUDE.md":
        return ["claude"]
    return []


def _is_executable(path: Path) -> bool:
    """检查文件是否有可执行权限位（owner/group/other 的 x 位）。"""
    return bool(path.stat().st_mode & 0o111)
