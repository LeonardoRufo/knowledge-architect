from __future__ import annotations

from typing import Protocol

from knowledge_architect.core import KnowledgeEvent, SourceDocument


class EventFactoryPort(Protocol):
    """Contract for translating a normalized document into an event."""

    def __call__(self, document: SourceDocument) -> KnowledgeEvent: ...
