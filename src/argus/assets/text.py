from __future__ import annotations

"""文本处理工具模块。

提供资产名称归一化、token 提取和有意义 token 过滤等文本处理工具。
用于支撑资产的重复检测、冲突检测和学习-资产关联匹配。

关键概念：
- normalize: 将文本转为小写、非字母数字替换为空格
- tokens: 提取长度 >= 4 的单词
- meaningful_tokens: 过滤掉泛型词汇后剩下的有区分度的 token
"""


# 泛型匹配词汇黑名单：这些词在资产领域中出现频率极高但区分度极低，
# 过滤它们可以显著提高匹配质量，减少假阳性关联。
GENERIC_MATCH_TOKENS = {
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


def tokens(text: str) -> set[str]:
    """从文本中提取所有长度 >= 4 的 token。

    要求最小长度 4 是为了过滤掉 "id"、"to" 等无意义短词。
    """
    return {token for token in normalize(text).split() if len(token) >= 4}


def meaningful_tokens(text: str) -> set[str]:
    """从文本中提取有意义的 token（排除泛型词汇）。

    在 tokens() 的基础上，过滤掉 GENERIC_MATCH_TOKENS 中的词汇。
    这一步对提高资产名称匹配的准确率至关重要，
    因为 "skill"、"plugin" 等词本身没有区分能力。
    """
    return {token for token in tokens(text) if token not in GENERIC_MATCH_TOKENS}


def normalize(text: str) -> str:
    """归一化文本：转小写，并将非字母数字字符替换为空格。

    例如 "Git-Skill_v2" → "git skill v2"。
    这样不同命名风格（camelCase、kebab-case、snake_case）的资产名称
    统一为可比较的格式。
    """
    return "".join(char.lower() if char.isalnum() else " " for char in text)
