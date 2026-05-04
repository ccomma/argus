from __future__ import annotations

import json
from pathlib import Path

from argus.ledger.models import EventRecord
from argus.ledger.store import EventLedger

from .base import BaseAdapter


class ClaudeAdapter(BaseAdapter):
    """Adapter for Claude Code conversation transcripts.

    Reads Claude Code JSONL transcript files and normalizes each record
    into an Argus EventRecord. Claude transcript fields differ from Codex:
    Claude uses ``type`` instead of ``event_type``, ``message`` for content,
    and stores tool results under ``tool_use`` blocks.
    """

    def __init__(self, ledger: EventLedger) -> None:
        self._ledger = ledger

    @property
    def agent_name(self) -> str:
        return "claude"

    def normalize_event(self, raw: dict) -> EventRecord:
        event_type = raw.get("type") or raw.get("event_type", "unknown")
        evidence: dict = raw.get("message") if isinstance(raw.get("message"), dict) else raw
        return EventRecord.create(
            source="claude_adapter",
            agent="claude",
            session=raw.get("session_id") or raw.get("session", ""),
            timestamp=raw.get("timestamp", ""),
            event_type=event_type,
            evidence=evidence,
        )

    def submit_event(self, event: EventRecord) -> str:
        self._ledger.append(event)
        return event.id

    def ingest_transcript(self, path: str | Path) -> int:
        events: list[EventRecord] = []
        for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid transcript JSONL at line {line_number}: {exc.msg}") from exc
            events.append(self.normalize_event(raw))
        return self._ledger.append_many(events)
