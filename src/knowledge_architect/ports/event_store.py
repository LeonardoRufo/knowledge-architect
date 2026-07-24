from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from knowledge_architect.core import KnowledgeEvent


class EventStorePort(Protocol):
    """Application-facing contract for persisting and replaying events."""

    def append(self, events: Iterable[KnowledgeEvent]) -> int: ...

    def list_events(self) -> list[KnowledgeEvent]: ...

    def count(self) -> int: ...
