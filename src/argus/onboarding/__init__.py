"""仓库入职模块 - 为新仓库生成入职包，包含规则、能力需求、角色推荐和初始化步骤。"""

from __future__ import annotations

from argus.onboarding.models import OnboardingPack
from argus.onboarding.generator import OnboardingGenerator

__all__ = ["OnboardingGenerator", "OnboardingPack"]
