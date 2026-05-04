from __future__ import annotations

"""能力资产核心模型模块。

定义能力资产的数据模型，包括：
- CapabilityAsset: 单个能力资产的完整描述
- AssetScanProfile: 扫描配置文件（定义从哪里扫描资产）
- AssetScanResult: 扫描结果
- AssetLearningLink: 学习项与资产的关联
- AssetReport: 报告产物路径

还定义了资产的生命周期状态常量（ACTIVE/ARCHIVED/DISABLED/ISOLATED/DEPRECATED）。
"""

import json
from dataclasses import asdict, dataclass, field
from hashlib import sha1
from pathlib import Path
from typing import Any


# ── 资产状态常量 ──

ACTIVE = "active"
ARCHIVED = "archived"
DISABLED = "disabled"
ISOLATED = "isolated"
DEPRECATED = "deprecated"


# ── 资产实体模型 ──


@dataclass(frozen=True)
class CapabilityAsset:
    """单个能力资产。

    表示一个可被 AI 代理使用的能力单元。资产类型包括：
    - skill: 技能文件（如 SKILL.md 定义的可复用能力）
    - plugin: Codex 插件
    - mcp_server: MCP 协议服务器
    - rule: 行为规则文件（如 AGENTS.md、CLAUDE.md）
    - script: 可执行脚本（sh/py/js/ts）
    - memory: 持久化记忆文件

    Attributes:
        id: 基于内容哈希的唯一标识（asset-<sha1>）
        type: 资产类型
        source: 资产来源（local_skill / codex_plugin / mcp_config 等）
        install_path: 安装路径
        agents: 可使用该资产的代理列表
        permissions: 该资产需要的权限列表
        risk_score: 风险评分（0-1）
        status: 生命周期状态
    """

    id: str
    name: str
    type: str
    source: str
    version: str
    install_path: str
    agents: list[str]
    scope: str
    permissions: list[str]
    risk_score: float
    status: str = ACTIVE
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CapabilityAsset:
        return cls(**data)

    @classmethod
    def create(
        cls,
        *,
        name: str,
        type: str,
        source: str,
        install_path: str | Path,
        version: str = "",
        agents: list[str] | None = None,
        scope: str = "local",
        permissions: list[str] | None = None,
        risk_score: float = 0.1,
        status: str = ACTIVE,
        metadata: dict[str, Any] | None = None,
    ) -> CapabilityAsset:
        """工厂方法：基于关键字段创建资产。

        使用 name + type + source + install_path 的组合 SHA1 生成
        确定性 ID，确保同一资产不会因重复扫描而产生多条记录。
        """
        path = str(Path(install_path))
        payload = {"name": name, "type": type, "source": source, "install_path": path}
        digest = sha1(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]
        return cls(
            id=f"asset-{digest}",
            name=name,
            type=type,
            source=source,
            version=version,
            install_path=path,
            agents=agents or [],
            scope=scope,
            permissions=permissions or [],
            risk_score=risk_score,
            status=status,
            metadata=metadata or {},
        )


# ── 辅助模型 ──


@dataclass(frozen=True)
class AssetLearningLink:
    """学习项与资产的关联记录。

    通过文本匹配建立学习项和资产之间的关联，用于追溯
    哪些资产可以从特定学习经验中受益。

    Attributes:
        learning_id: 关联的学习项 ID
        asset_id: 关联的资产 ID
        reason: 关联理由（匹配了哪些 token）
        confidence: 关联置信度
    """

    learning_id: str
    asset_id: str
    reason: str
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AssetScanResult:
    """资产扫描结果。

    包含扫描发现的所有资产和警告信息。
    """

    assets: list[CapabilityAsset]
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AssetReport:
    """资产报告的产物路径。

    包含扫描报告路径和可选的链接报告路径。
    """

    report_path: Path
    link_report_path: Path | None = None


# ── 扫描配置文件 ──


@dataclass(frozen=True)
class AssetScanProfile:
    """资产扫描配置文件。

    定义扫描器应从哪些目录和文件中发现各类资产。
    六类扫描源：
    - skill_dirs: 技能文件目录
    - plugin_dirs: 插件清单目录
    - mcp_configs: MCP 服务配置文件
    - rule_files: 行为规则文件
    - script_dirs: 脚本目录
    - memory_dirs: 记忆文件目录
    """

    skill_dirs: list[Path] = field(default_factory=list)
    plugin_dirs: list[Path] = field(default_factory=list)
    mcp_configs: list[Path] = field(default_factory=list)
    rule_files: list[Path] = field(default_factory=list)
    script_dirs: list[Path] = field(default_factory=list)
    memory_dirs: list[Path] = field(default_factory=list)

    def to_scan_kwargs(self) -> dict[str, list[Path]]:
        """将配置文件转换为 scan() 方法的关键字参数。"""
        return {
            "skill_dirs": self.skill_dirs,
            "plugin_dirs": self.plugin_dirs,
            "mcp_configs": self.mcp_configs,
            "rule_files": self.rule_files,
            "script_dirs": self.script_dirs,
            "memory_dirs": self.memory_dirs,
        }

    def merged_with(
        self,
        *,
        skill_dirs: list[str | Path],
        plugin_dirs: list[str | Path],
        mcp_configs: list[str | Path],
        rule_files: list[str | Path],
        script_dirs: list[str | Path],
        memory_dirs: list[str | Path],
    ) -> AssetScanProfile:
        """将默认配置与用户显式指定的路径合并。

        显式路径追加到默认路径之后，且自动去重（相同路径不重复出现）。
        这样可以让本地 codex 配置作为基础，用户额外添加自定义路径。
        """
        return AssetScanProfile(
            skill_dirs=_merge_paths(self.skill_dirs, skill_dirs),
            plugin_dirs=_merge_paths(self.plugin_dirs, plugin_dirs),
            mcp_configs=_merge_paths(self.mcp_configs, mcp_configs),
            rule_files=_merge_paths(self.rule_files, rule_files),
            script_dirs=_merge_paths(self.script_dirs, script_dirs),
            memory_dirs=_merge_paths(self.memory_dirs, memory_dirs),
        )


def local_codex_asset_profile(home: str | Path | None = None) -> AssetScanProfile:
    """生成本地 Codex 环境的默认扫描配置。

    自动扫描用户主目录下的标准 Codex/Agents 目录结构：
    - ~/.codex/skills 和 ~/.agents/skills: 技能文件
    - ~/.codex/plugins/cache: 已安装插件
    - ~/.codex/config.toml: MCP 服务配置
    - AGENTS.md 规则文件
    - ~/.codex/memories: 持久化记忆
    """
    root = Path(home).expanduser() if home else Path.home()
    codex_home = root / ".codex"
    agents_home = root / ".agents"
    return AssetScanProfile(
        skill_dirs=[codex_home / "skills", agents_home / "skills"],
        plugin_dirs=[codex_home / "plugins" / "cache"],
        mcp_configs=[codex_home / "config.toml"],
        rule_files=[codex_home / "AGENTS.md", codex_home / "superpowers" / "AGENTS.md"],
        memory_dirs=[codex_home / "memories"],
    )


def _merge_paths(defaults: list[Path], explicit: list[str | Path]) -> list[Path]:
    """合并默认路径和显式路径并去重。

    保持默认路径在前，显式路径在后的顺序，同时对完全相同的路径去重。
    """
    seen = set()
    result: list[Path] = []
    for path in [*defaults, *[Path(item) for item in explicit]]:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        result.append(path)
    return result
