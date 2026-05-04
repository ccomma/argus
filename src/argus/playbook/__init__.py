"""剧本模块：定义 AI Agent 执行工作的标准化流程模板。

Playbook 描述一套完整的任务执行模式：包含提问策略、确认点、
交付物模板、合同模板、角色分配和能力包清单。
PlaybookRegistry 提供剧本的持久化存储和检索能力。
"""

from __future__ import annotations

from argus.playbook.models import Playbook, PlaybookRegistry

__all__ = ["Playbook", "PlaybookRegistry"]
