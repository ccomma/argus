from __future__ import annotations

"""风险评分与推断模块。

提供能力资产的风险评估能力，包括：
- 权限到风险原因的映射
- 风险原因到风险等级（tier）的映射
- 单个资产的风险推断
- 能力包条目的聚合风险评估

风险等级体系（由低到高）：
    low → medium → high → critical
"""

from argus.assets import CapabilityAsset

from .models import CapabilityPackEntry, RiskInference


# ── 风险等级定义 ──

RISK_TIERS = ("low", "medium", "high", "critical")

# 权限到风险原因的映射表
# 每条权限对应一个风险原因代码，这些代码随后被映射到风险等级
RISK_REASON_BY_PERMISSION = {
    "read": "reads_files",
    "reads_files": "reads_files",
    "write": "writes_files",
    "writes_files": "writes_files",
    "network": "network_access",
    "network_access": "network_access",
    "process": "executes_commands",
    "executes_commands": "executes_commands",
    "secret": "uses_secrets",
    "uses_secrets": "uses_secrets",
    "external_service": "external_service",
}

# 风险原因到风险等级的映射表
# 关键风险等级：
# - critical: 使用密钥（可能导致凭证泄露）
# - high: 网络访问、改变代理行为、外部服务（扩大攻击面）
# - medium: 文件写入、执行命令（可造成持久化影响）
# - low: 只读文件（影响范围最小）
RISK_TIER_BY_REASON = {
    "reads_files": "low",
    "writes_files": "medium",
    "network_access": "high",
    "executes_commands": "medium",
    "changes_agent_behavior": "high",
    "uses_secrets": "critical",
    "external_service": "high",
    "unknown": "medium",
}


# ── 风险推断函数 ──


def infer_risk(reason_codes: list[str]) -> RiskInference:
    """根据风险原因代码列表推断风险等级。

    流程：
    1. 去重并排序原因代码（空列表时用 ["unknown"]）
    2. 遍历所有原因代码，找到最高风险等级
    3. 收集所有达到该最高等级的代码
    4. 返回包含等级、代码和文本原因的 RiskInference

    例如：["reads_files", "network_access"] → high（因为 network_access 为 high）
    """
    known_codes = sorted(set(reason_codes or ["unknown"]))
    highest = "low"
    highest_codes: list[str] = []
    for code in known_codes:
        tier = RISK_TIER_BY_REASON.get(code, "medium")
        if tier_rank(tier) > tier_rank(highest):
            highest = tier
            highest_codes = [code]
        elif tier == highest:
            highest_codes.append(code)
    return RiskInference(tier=highest, reason_codes=highest_codes, reason=", ".join(highest_codes))


def aggregate_risk(entries: list[CapabilityPackEntry]) -> RiskInference:
    """聚合多个能力包条目的风险。

    流程：
    1. 遍历所有条目的风险等级快照
    2. 取最高的风险等级
    3. 收集贡献该等级的条目 ID
    4. 生成包含条目引用的聚合原因字符串

    例如："reads_files, network_access; entries=entry-1,entry-3"
    这表示聚合风险为 high，由 entry-1 和 entry-3 贡献。
    """
    highest = "low"
    reason_codes: list[str] = []
    entry_ids: list[str] = []
    for entry in entries:
        tier = entry.risk_tier_snapshot
        if tier_rank(tier) > tier_rank(highest):
            highest = tier
            reason_codes = list(entry.inferred_reason_codes_snapshot)
            entry_ids = [entry.entry_id]
        elif tier == highest:
            reason_codes.extend(entry.inferred_reason_codes_snapshot)
            entry_ids.append(entry.entry_id)
    codes = sorted(set(reason_codes or ["reads_files"]))
    reason = ", ".join(codes)
    if entry_ids:
        reason = f"{reason}; entries={','.join(entry_ids)}"
    return RiskInference(tier=highest, reason_codes=codes, reason=reason)


def reason_codes_for_asset(asset: CapabilityAsset) -> list[str]:
    """从资产的权限列表映射到风险原因代码。

    将每条权限通过 RISK_REASON_BY_PERMISSION 表映射为风险原因代码。
    至少返回 ["reads_files"] 作为默认低风险代码。
    """
    codes = [RISK_REASON_BY_PERMISSION.get(permission, "unknown") for permission in asset.permissions]
    if not codes:
        codes = ["reads_files"]
    return sorted(set(codes))


def tier_rank(tier: str) -> int:
    """将风险等级字符串转换为数值（0-3），用于比较。

    low=0, medium=1, high=2, critical=3。
    未知等级默认按 medium(1) 处理。
    """
    return RISK_TIERS.index(tier) if tier in RISK_TIERS else RISK_TIERS.index("medium")


def highest_risk_entry_ids(entries: list[CapabilityPackEntry], tier: str) -> list[str]:
    """获取处于指定风险等级的所有条目的 entry_id 列表。

    用于在能力包清单中标注哪些条目贡献了最高的聚合风险。
    """
    return [entry.entry_id for entry in entries if entry.risk_tier_snapshot == tier]
