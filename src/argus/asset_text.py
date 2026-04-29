from __future__ import annotations


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
    return {token for token in normalize(text).split() if len(token) >= 4}


def meaningful_tokens(text: str) -> set[str]:
    return {token for token in tokens(text) if token not in GENERIC_MATCH_TOKENS}


def normalize(text: str) -> str:
    return "".join(char.lower() if char.isalnum() else " " for char in text)
