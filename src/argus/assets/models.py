from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from hashlib import sha1
from pathlib import Path
from typing import Any


ACTIVE = "active"
ARCHIVED = "archived"
DISABLED = "disabled"
ISOLATED = "isolated"
DEPRECATED = "deprecated"


@dataclass(frozen=True)
class CapabilityAsset:
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


@dataclass(frozen=True)
class AssetLearningLink:
    learning_id: str
    asset_id: str
    reason: str
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AssetScanResult:
    assets: list[CapabilityAsset]
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AssetReport:
    report_path: Path
    link_report_path: Path | None = None


@dataclass(frozen=True)
class AssetScanProfile:
    skill_dirs: list[Path] = field(default_factory=list)
    plugin_dirs: list[Path] = field(default_factory=list)
    mcp_configs: list[Path] = field(default_factory=list)
    rule_files: list[Path] = field(default_factory=list)
    script_dirs: list[Path] = field(default_factory=list)
    memory_dirs: list[Path] = field(default_factory=list)

    def to_scan_kwargs(self) -> dict[str, list[Path]]:
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
        return AssetScanProfile(
            skill_dirs=_merge_paths(self.skill_dirs, skill_dirs),
            plugin_dirs=_merge_paths(self.plugin_dirs, plugin_dirs),
            mcp_configs=_merge_paths(self.mcp_configs, mcp_configs),
            rule_files=_merge_paths(self.rule_files, rule_files),
            script_dirs=_merge_paths(self.script_dirs, script_dirs),
            memory_dirs=_merge_paths(self.memory_dirs, memory_dirs),
        )


def local_codex_asset_profile(home: str | Path | None = None) -> AssetScanProfile:
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
    seen = set()
    result: list[Path] = []
    for path in [*defaults, *[Path(item) for item in explicit]]:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        result.append(path)
    return result
