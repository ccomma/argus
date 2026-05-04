"""反馈闭环实现：定义反馈信号模型和反馈采集、聚合、推荐的完整流程。

反馈闭环是 Argus 自优化能力的核心：Agent 执行结果以信号形式反馈到系统，
通过聚合分析产生对能力资产的提升、修订或弃用建议。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class FeedbackSignal:
    """反馈信号（不可变数据类）。

    记录一条来自特定来源的反馈信号，包含信号类型（success/failure/correction）、
    目标资产、信号强度和相关证据。
    """
    signal_id: str
    source_type: str
    source_id: str
    signal_type: str
    target_type: str
    target_id: str
    strength: float
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典。"""
        return {
            "signal_id": self.signal_id,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "signal_type": self.signal_type,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "strength": self.strength,
            "evidence": self.evidence,
        }


class FeedbackLoop:
    """反馈闭环管理器。

    职责：
    1. 记录反馈信号（持久化为独立 JSON 文件）
    2. 按目标类型/ID/信号类型筛选查询
    3. 聚合计算信号强度平均值
    4. 基于聚合结果生成治理推荐（promote/revise/review_or_deprecate/observe）
    """

    def __init__(self, store_dir: Path) -> None:
        self.store_dir = Path(store_dir)

    def record(
        self,
        source_type: str,
        source_id: str,
        signal_type: str,
        target_type: str,
        target_id: str,
        strength: float,
        evidence: dict | None = None,
    ) -> FeedbackSignal:
        """记录一条反馈信号。

        1. 基于来源、目标和时间戳生成 SHA-1 哈希作为 signal_id（取前 12 位）
        2. 构造 FeedbackSignal 对象
        3. 持久化为 {signal_id}.json 文件
        4. 返回创建的信号对象
        """
        import hashlib
        import time
        raw = f"{source_type}{source_id}{signal_type}{target_type}{target_id}{time.time()}"
        signal_id = hashlib.sha1(raw.encode()).hexdigest()[:12]
        signal = FeedbackSignal(
            signal_id=signal_id,
            source_type=source_type,
            source_id=source_id,
            signal_type=signal_type,
            target_type=target_type,
            target_id=target_id,
            strength=strength,
            evidence=evidence or {},
        )
        self.store_dir.mkdir(parents=True, exist_ok=True)
        path = self.store_dir / f"{signal_id}.json"
        path.write_text(json.dumps(signal.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
        return signal

    def list_signals(
        self,
        target_type: str = "",
        target_id: str = "",
        signal_type: str = "",
    ) -> list[FeedbackSignal]:
        """按条件筛选反馈信号列表。

        所有筛选条件均为可选，空值表示不筛选该维度。
        多个条件之间为 AND 关系。
        """
        if not self.store_dir.exists():
            return []
        results: list[FeedbackSignal] = []
        for f in self.store_dir.glob("*.json"):
            data = json.loads(f.read_text(encoding="utf-8"))
            signal = FeedbackSignal(
                signal_id=data["signal_id"],
                source_type=data["source_type"],
                source_id=data["source_id"],
                signal_type=data["signal_type"],
                target_type=data["target_type"],
                target_id=data["target_id"],
                strength=data["strength"],
                evidence=data.get("evidence", {}),
            )
            if target_type and signal.target_type != target_type:
                continue
            if target_id and signal.target_id != target_id:
                continue
            if signal_type and signal.signal_type != signal_type:
                continue
            results.append(signal)
        return results

    def aggregate_strength(
        self,
        target_type: str,
        target_id: str,
        signal_type: str = "",
    ) -> float:
        """计算指定目标反馈信号的平均强度，无信号时返回 0.0。"""
        signals = self.list_signals(target_type, target_id, signal_type)
        if not signals:
            return 0.0
        return sum(s.strength for s in signals) / len(signals)

    def compute_recommendation(
        self,
        target_type: str,
        target_id: str,
    ) -> dict[str, Any]:
        """计算资产治理推荐。

        1. 聚合 success/failure/correction 三类信号强度
        2. 计算净评分: net_score = promote - demote - (revise * 0.5)
           — revise 权重为 0.5，因为修正信号既非完全正面也非完全负面
        3. 推荐逻辑:
           - net_score > 0.3 且信号数 >= 3: promote（提升，建议推广）
           - net_score < -0.3: review_or_deprecate（审查或弃用）
           - revise > 0.3: revise（修订，需要改进）
           - 其他: observe（观察中，数据不足）
        4. 返回包含所有中间计算值和最终推荐的字典
        """
        promote = self.aggregate_strength(target_type, target_id, "success")
        demote = self.aggregate_strength(target_type, target_id, "failure")
        revise = self.aggregate_strength(target_type, target_id, "correction")
        total_signals = len(self.list_signals(target_type, target_id))
        # 修正信号贡献负向影响，但权重低于失败信号
        net_score = promote - demote - (revise * 0.5)

        # 决策阈值说明：
        # net_score > 0.3: 正面信号显著占优，且有足够样本量
        # net_score < -0.3: 负面信号占优，需要审查
        # revise > 0.3: 大量修正信号，说明需要调整
        # 其他情况: 数据不足以做出明确判断
        if net_score > 0.3 and total_signals >= 3:
            recommendation = "promote"
        elif net_score < -0.3:
            recommendation = "review_or_deprecate"
        elif revise > 0.3:
            recommendation = "revise"
        else:
            recommendation = "observe"

        return {
            "target_type": target_type,
            "target_id": target_id,
            "promote_strength": promote,
            "demote_strength": demote,
            "revise_strength": revise,
            "net_score": net_score,
            "total_signals": total_signals,
            "recommendation": recommendation,
        }
