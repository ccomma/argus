from __future__ import annotations

import json
import tomllib
from dataclasses import asdict, dataclass, field
from hashlib import sha1
from pathlib import Path
from typing import Any, Callable

from argus.learning import CandidateLearningItem


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


class CapabilityAssetScanner:
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
        assets: list[CapabilityAsset] = []
        warnings: list[str] = []
        assets.extend(_collect(skill_dirs or [], _scan_skill_dir, warnings))
        assets.extend(_collect(plugin_dirs or [], _scan_plugin_dir, warnings))
        assets.extend(_collect(mcp_configs or [], _scan_mcp_config, warnings))
        assets.extend(_collect(rule_files or [], _scan_rule_file, warnings))
        assets.extend(_collect(script_dirs or [], _scan_script_dir, warnings))
        assets.extend(_collect(memory_dirs or [], _scan_memory_dir, warnings))
        return AssetScanResult(assets=_deduplicate_assets(assets), warnings=warnings)


class CapabilityInventory:
    def __init__(self, inventory_path: str | Path) -> None:
        self.inventory_path = Path(inventory_path)

    def write(self, assets: list[CapabilityAsset]) -> None:
        self.inventory_path.parent.mkdir(parents=True, exist_ok=True)
        self.inventory_path.write_text(
            json.dumps([asset.to_dict() for asset in assets], indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def list_assets(self) -> list[CapabilityAsset]:
        if not self.inventory_path.exists():
            return []
        data = json.loads(self.inventory_path.read_text(encoding="utf-8"))
        return [CapabilityAsset.from_dict(item) for item in data]


class AssetReporter:
    def __init__(self, reports_dir: str | Path) -> None:
        self.reports_dir = Path(reports_dir)

    def write(
        self,
        assets: list[CapabilityAsset],
        *,
        warnings: list[str] | None = None,
        links: list[AssetLearningLink] | None = None,
    ) -> AssetReport:
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        report_path = self.reports_dir / "asset-scan-report.md"
        link_report_path = self.reports_dir / "candidate-asset-links.json"
        report_path.write_text(_markdown_report(assets, warnings or [], links or []), encoding="utf-8")
        if links is not None:
            link_report_path.write_text(
                json.dumps([link.to_dict() for link in links], indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            return AssetReport(report_path=report_path, link_report_path=link_report_path)
        return AssetReport(report_path=report_path)


class CandidateAssetLinker:
    def link(self, learnings: list[CandidateLearningItem], assets: list[CapabilityAsset]) -> list[AssetLearningLink]:
        links: list[AssetLearningLink] = []
        for learning in learnings:
            learning_tokens = _meaningful_tokens(
                " ".join([learning.summary, learning.type, learning.scope, learning.reverse_learning_target])
            )
            for asset in assets:
                asset_tokens = _asset_match_tokens(asset)
                matched = learning_tokens & asset_tokens
                if not matched:
                    continue
                links.append(
                    AssetLearningLink(
                        learning_id=learning.id,
                        asset_id=asset.id,
                        reason=f"matched tokens: {', '.join(sorted(matched))}",
                        confidence=min(0.9, 0.45 + 0.1 * len(matched)),
                    )
                )
        return links


def _collect(
    paths: list[str | Path],
    scanner: Callable[[Path], list[CapabilityAsset]],
    warnings: list[str],
) -> list[CapabilityAsset]:
    assets: list[CapabilityAsset] = []
    for path in paths:
        try:
            assets.extend(scanner(Path(path)))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            warnings.append(f"{path}: {exc}")
    return assets


def _scan_skill_dir(root: Path) -> list[CapabilityAsset]:
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
            risk_score=0.2,
            metadata={"manifest": str(skill_file)},
        )
        for skill_file in skill_files
        if skill_file.is_file()
    ]


def _scan_plugin_dir(root: Path) -> list[CapabilityAsset]:
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
    seen = set()
    result = []
    for asset in sorted(assets, key=lambda item: (item.type, item.name, item.install_path)):
        if asset.id in seen:
            continue
        seen.add(asset.id)
        result.append(asset)
    return result


def _plugin_permissions(data: dict[str, Any]) -> list[str]:
    permissions = data.get("permissions") or data.get("capabilities") or []
    if isinstance(permissions, dict):
        return sorted(str(key) for key, enabled in permissions.items() if enabled)
    if isinstance(permissions, list):
        return sorted(str(permission) for permission in permissions)
    return []


def _mcp_permissions(config: dict[str, Any]) -> list[str]:
    permissions = []
    if config.get("command"):
        permissions.append("process")
    if config.get("env"):
        permissions.append("environment")
    if config.get("url"):
        permissions.append("network")
    return permissions


def _load_config(path: Path) -> dict[str, Any]:
    if path.suffix == ".toml":
        with path.open("rb") as handle:
            return tomllib.load(handle)
    return json.loads(path.read_text(encoding="utf-8"))


def _rule_agents(path: Path) -> list[str]:
    if path.name == "AGENTS.md":
        return ["codex"]
    if path.name == "CLAUDE.md":
        return ["claude"]
    return []


def _is_executable(path: Path) -> bool:
    return bool(path.stat().st_mode & 0o111)


def _tokens(text: str) -> set[str]:
    return {token for token in _normalize(text).split() if len(token) >= 4}


def _meaningful_tokens(text: str) -> set[str]:
    return {token for token in _tokens(text) if token not in _GENERIC_MATCH_TOKENS}


def _asset_match_tokens(asset: CapabilityAsset) -> set[str]:
    metadata_text = " ".join(str(value) for value in asset.metadata.values())
    return _meaningful_tokens(
        " ".join(
            [
                asset.name,
                Path(asset.install_path).stem,
                Path(asset.install_path).parent.name,
                " ".join(asset.permissions),
                metadata_text,
            ]
        )
    )


def _normalize(text: str) -> str:
    return "".join(char.lower() if char.isalnum() else " " for char in text)


_GENERIC_MATCH_TOKENS = {
    "agent",
    "asset",
    "capability",
    "codex",
    "config",
    "local",
    "memory",
    "pack",
    "plugin",
    "project",
    "script",
    "skill",
    "tool",
}


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


def _markdown_report(
    assets: list[CapabilityAsset],
    warnings: list[str],
    links: list[AssetLearningLink],
) -> str:
    by_type: dict[str, int] = {}
    duplicates = find_potential_duplicates(assets)
    conflicts = find_potential_conflicts(assets)
    risky_assets = [asset for asset in assets if asset.risk_score >= 0.5]
    risk_counts = {"low": 0, "medium": 0, "high": 0}
    for asset in assets:
        by_type[asset.type] = by_type.get(asset.type, 0) + 1
        if asset.risk_score >= 0.7:
            risk_counts["high"] += 1
        elif asset.risk_score >= 0.4:
            risk_counts["medium"] += 1
        else:
            risk_counts["low"] += 1
    lines = [
        "# Argus Capability Asset Report",
        "",
        f"- Assets: {len(assets)}",
        f"- Candidate Links: {len(links)}",
        f"- Risk: low={risk_counts['low']}, medium={risk_counts['medium']}, high={risk_counts['high']}",
        "",
        "## Assets By Type",
        "",
    ]
    if not by_type:
        lines.append("No capability assets found.")
    for asset_type, count in sorted(by_type.items()):
        lines.append(f"- {asset_type}: {count}")
    if duplicates:
        lines.extend(["", "## Potential Duplicates", ""])
        for group in duplicates:
            names = ", ".join(f"{asset.name} ({asset.type})" for asset in group)
            lines.append(f"- {names}")
    if conflicts:
        lines.extend(["", "## Potential Conflicts", ""])
        for group in conflicts:
            names = ", ".join(f"{asset.name} ({asset.type})" for asset in group)
            lines.append(f"- {names}")
    if risky_assets:
        lines.extend(["", "## Risky Assets", ""])
        for asset in sorted(risky_assets, key=lambda item: (-item.risk_score, item.type, item.name)):
            permissions = ", ".join(asset.permissions) or "none"
            lines.append(f"- {asset.name} ({asset.type}): risk={asset.risk_score}, permissions={permissions}")
    if warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in warnings)
    return "\n".join(lines) + "\n"


def find_potential_duplicates(assets: list[CapabilityAsset]) -> list[list[CapabilityAsset]]:
    groups: dict[str, list[CapabilityAsset]] = {}
    for asset in assets:
        key = _normalized_asset_name(asset.name)
        groups.setdefault(key, []).append(asset)
    return [group for _, group in sorted(groups.items()) if len(group) > 1]


def find_potential_conflicts(assets: list[CapabilityAsset]) -> list[list[CapabilityAsset]]:
    groups: dict[str, list[CapabilityAsset]] = {}
    for asset in assets:
        if asset.type not in {"skill", "rule", "memory", "plugin"}:
            continue
        groups.setdefault(_normalized_asset_name(asset.name), []).append(asset)
    return [
        group
        for _, group in sorted(groups.items())
        if len(group) > 1 and _group_has_shared_agent_or_behavior_scope(group)
    ]


def _group_has_shared_agent_or_behavior_scope(group: list[CapabilityAsset]) -> bool:
    agent_sets = [set(asset.agents) for asset in group if asset.agents]
    for index, agents in enumerate(agent_sets):
        if any(agents & other for other in agent_sets[index + 1 :]):
            return True
    return len({asset.type for asset in group}) > 1


def _normalized_asset_name(name: str) -> str:
    normalized = _normalize(name)
    for suffix in (" skill", " plugin", " script", " server"):
        if normalized.endswith(suffix):
            normalized = normalized[: -len(suffix)]
    return " ".join(normalized.split())
