from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from knowledge_architect.core import KnowledgeEvent


def materialize(events: Iterable[KnowledgeEvent]) -> dict[str, Any]:
    """Materialize the minimal v0.1 knowledge state from immutable events."""

    documents: dict[str, dict[str, Any]] = {}
    for event in events:
        if event.event_type == "source_document_observed":
            documents[event.source_id] = {
                "source_system": event.source_system,
                "source_id": event.source_id,
                **event.payload,
            }

    return {
        "schema_version": "kaa-state-0.1",
        "documents": sorted(documents.values(), key=lambda item: item.get("title", "")),
        "statistics": {"documents": len(documents)},
    }
