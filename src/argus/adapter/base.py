from __future__ import annotations

from abc import ABC, abstractmethod

from argus.ledger.models import EventRecord


class BaseAdapter(ABC):
    @property
    @abstractmethod
    def agent_name(self) -> str: ...

    @abstractmethod
    def normalize_event(self, raw: dict) -> EventRecord: ...

    def submit_event(self, event: EventRecord) -> str:
        return event.id
