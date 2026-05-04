"""版本锁定模块：管理能力资产的版本固定与锁定机制。

通过 VersionLock 实现资产版本的确定性锁定，防止意外升级导致的不兼容问题。
LockEntry 记录单条锁定信息，VersionLock 管理所有锁定并支持持久化为锁文件。
"""

from __future__ import annotations

from argus.versioning.models import LockEntry, VersionLock

__all__ = ["LockEntry", "VersionLock"]
