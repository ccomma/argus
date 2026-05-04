"""反馈模块：收集和分析 Agent 执行反馈信号，驱动持续改进。

FeedbackLoop 记录成功/失败/修正等反馈信号，通过聚合分析生成
promote（提升）/ revise（修订）/ review_or_deprecate（审查或弃用）等推荐决策，
实现能力操作系统的自优化闭环。
"""

from __future__ import annotations

from argus.feedback.loop import FeedbackLoop

__all__ = ["FeedbackLoop"]
