import json
import tempfile
import unittest
from pathlib import Path

from argus.adapter import BaseAdapter, ClaudeAdapter, CodexAdapter
from argus.assets import CapabilityAsset, CapabilityInventory
from argus.capability_packs import CapabilityPackStore, RolePackStore
from argus.ledger import EventLedger, LearningLedger
from argus.ledger.models import EventRecord
from argus.storage import ContractStorage


class Phase8AdapterTest(unittest.TestCase):
    def test_base_adapter_is_abstract(self):
        with self.assertRaises(TypeError):
            BaseAdapter()

    def test_codex_adapter_has_agent_name(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = EventLedger(Path(tmpdir) / "events.jsonl")
            adapter = CodexAdapter(ledger)
            self.assertEqual(adapter.agent_name, "codex")

    def test_codex_adapter_normalizes_event(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = EventLedger(Path(tmpdir) / "events.jsonl")
            adapter = CodexAdapter(ledger)
            raw = {"session": "s1", "timestamp": "2025-01-01", "event_type": "command_failed", "evidence": {"cmd": "test"}}
            event = adapter.normalize_event(raw)
            self.assertEqual(event.agent, "codex")
            self.assertEqual(event.source, "codex_adapter")
            self.assertEqual(event.event_type, "command_failed")

    def test_codex_adapter_submits_event_to_ledger(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = EventLedger(Path(tmpdir) / "events.jsonl")
            adapter = CodexAdapter(ledger)
            raw = {"session": "s1", "timestamp": "2025-01-01", "event_type": "test", "evidence": {}}
            event = adapter.normalize_event(raw)
            eid = adapter.submit_event(event)
            self.assertEqual(eid, event.id)
            events = ledger.list_events()
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].id, event.id)

    def test_codex_adapter_ingests_transcript_fixture(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            transcript = Path(tmpdir) / "transcript.jsonl"
            transcript.write_text(
                json.dumps({"session": "s1", "timestamp": "t1", "event_type": "user_correction", "evidence": {"msg": "fix"}})
                + "\n",
                encoding="utf-8",
            )
            ledger = EventLedger(Path(tmpdir) / "events.jsonl")
            adapter = CodexAdapter(ledger)
            count = adapter.ingest_transcript(str(transcript))
            self.assertEqual(count, 1)
            events = ledger.list_events()
            self.assertEqual(events[0].source, "codex_transcript")

    def test_claude_adapter_has_agent_name(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = EventLedger(Path(tmpdir) / "events.jsonl")
            adapter = ClaudeAdapter(ledger)
            self.assertEqual(adapter.agent_name, "claude")

    def test_claude_adapter_normalizes_claude_event_type_field(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = EventLedger(Path(tmpdir) / "events.jsonl")
            adapter = ClaudeAdapter(ledger)
            raw = {"type": "tool_use", "session_id": "s1", "timestamp": "t1", "message": {"content": "hello"}}
            event = adapter.normalize_event(raw)
            self.assertEqual(event.agent, "claude")
            self.assertEqual(event.source, "claude_adapter")
            self.assertEqual(event.event_type, "tool_use")
            self.assertEqual(event.evidence["content"], "hello")

    def test_claude_adapter_normalizes_event_with_event_type_fallback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = EventLedger(Path(tmpdir) / "events.jsonl")
            adapter = ClaudeAdapter(ledger)
            raw = {"event_type": "custom_event", "session": "s2", "timestamp": "t2", "message": {"text": "hi"}}
            event = adapter.normalize_event(raw)
            self.assertEqual(event.event_type, "custom_event")

    def test_claude_adapter_ingests_transcript(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            transcript = Path(tmpdir) / "transcript.jsonl"
            transcript.write_text(
                json.dumps({"type": "user_message", "session_id": "abc", "timestamp": "t3", "message": {"text": "ok"}}) + "\n",
                encoding="utf-8",
            )
            ledger = EventLedger(Path(tmpdir) / "events.jsonl")
            adapter = ClaudeAdapter(ledger)
            count = adapter.ingest_transcript(str(transcript))
            self.assertEqual(count, 1)
            events = ledger.list_events()
            self.assertEqual(events[0].source, "claude_adapter")


if __name__ == "__main__":
    unittest.main()
