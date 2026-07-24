from __future__ import annotations

from typing import Any, Protocol

from knowledge_architect.core import KnowledgeEvent

ProjectionState = dict[str, Any]


class ProjectionPort(Protocol):
    """Pure deterministic reducer from events to a named materialized view."""

    name: str
    version: int

    def initial_state(self) -> ProjectionState: ...

    def apply(self, state: ProjectionState, event: KnowledgeEvent) -> ProjectionState: ...

    def finalize(self, state: ProjectionState) -> ProjectionState: ...
