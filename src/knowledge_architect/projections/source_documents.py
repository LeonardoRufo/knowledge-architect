from __future__ import annotations

from copy import deepcopy
from typing import Any

from knowledge_architect.core import SOURCE_DOCUMENT_OBSERVED, KnowledgeEvent
from knowledge_architect.ports import ProjectionState


class SourceDocumentProjection:
    """Latest normalized representation of every observed source document."""

    name = "source_documents"
    version = 1

    def initial_state(self) -> ProjectionState:
        return {"documents_by_key": {}}

    def apply(self, state: ProjectionState, event: KnowledgeEvent) -> ProjectionState:
        if event.event_type != SOURCE_DOCUMENT_OBSERVED:
            return state

        next_state = deepcopy(state)
        documents = next_state["documents_by_key"]
        key = f"{event.source_system}:{event.source_id}"
        documents[key] = {
            "source_system": event.source_system,
            "source_id": event.source_id,
            **event.payload,
        }
        return next_state

    def finalize(self, state: ProjectionState) -> ProjectionState:
        documents_by_key: dict[str, dict[str, Any]] = state["documents_by_key"]
        documents = sorted(
            documents_by_key.values(),
            key=lambda item: (
                str(item.get("title", "")).casefold(),
                str(item.get("source_system", "")),
                str(item.get("source_id", "")),
            ),
        )
        return {
            "schema_version": "kaa-source-documents-1",
            "documents": documents,
            "statistics": {"documents": len(documents)},
        }
