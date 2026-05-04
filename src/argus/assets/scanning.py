from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any, Callable

from argus.assets.models import AssetScanProfile, AssetScanResult, CapabilityAsset


class CapabilityAssetScanner:
    def scan_profile(self, profile: AssetScanProfile) -> AssetScanResult:
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
