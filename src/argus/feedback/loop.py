from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class FeedbackSignal:
    signal_id: str
    source_type: str
    source_id: str
    signal_type: str
    target_type: str
    target_id: str
    strength: float
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
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
        signals = self.list_signals(target_type, target_id, signal_type)
        if not signals:
            return 0.0
        return sum(s.strength for s in signals) / len(signals)

    def compute_recommendation(
        self,
        target_type: str,
        target_id: str,
    ) -> dict[str, Any]:
        promote = self.aggregate_strength(target_type, target_id, "success")
        demote = self.aggregate_strength(target_type, target_id, "failure")
        revise = self.aggregate_strength(target_type, target_id, "correction")
        total_signals = len(self.list_signals(target_type, target_id))
        net_score = promote - demote - (revise * 0.5)

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
