from __future__ import annotations

from typing import Protocol

from knowledge_architect.core import SourceDocument


class SourceProviderPort(Protocol):
    """Application-facing contract for acquiring normalized source documents."""

    def fetch(self, source_id: str) -> SourceDocument: ...
