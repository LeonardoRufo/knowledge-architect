from __future__ import annotations

from typing import Protocol

from knowledge_architect.core import SourceDocument


class KnowledgeConnector(Protocol):
    def discover(self, query: str | None = None) -> list[dict]: ...

    def fetch(self, source_id: str) -> SourceDocument: ...
