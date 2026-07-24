from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from knowledge_architect.core import KnowledgeEvent, StoredEvent


class EventStorePort(Protocol):
    """Application-facing contract for persisting and replaying events."""

    def append(self, events: Iterable[KnowledgeEvent]) -> int: ...

    def list_events(self) -> list[KnowledgeEvent]: ...

    def list_stream(self, *, after_sequence: int = 0) -> list[StoredEvent]: ...

    def count(self) -> int: ...
