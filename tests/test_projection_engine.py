from __future__ import annotations

from knowledge_architect.application import (
    RebuildProjectionCommand,
    RebuildProjectionHandler,
)
from knowledge_architect.core import KnowledgeEvent
from knowledge_architect.event_store import SQLiteEventStore
from knowledge_architect.projection_store import SQLiteProjectionStore
from knowledge_architect.projections import ProjectionRegistry, SourceDocumentProjection


def _event(source_id: str, title: str, content: str) -> KnowledgeEvent:
    return KnowledgeEvent(
        event_type="source_document_observed",
        source_system="notion",
        source_id=source_id,
        payload={"title": title, "content_markdown": content},
    )


def _handler(path) -> RebuildProjectionHandler:
    return RebuildProjectionHandler(
        event_store=SQLiteEventStore(path),
        projection_store=SQLiteProjectionStore(path),
        registry=ProjectionRegistry([SourceDocumentProjection()]),
    )


def test_rebuild_projection_replays_ordered_stream(tmp_path) -> None:
    path = tmp_path / "events.db"
    store = SQLiteEventStore(path)
    store.append([_event("page-1", "Old", "A"), _event("page-1", "New", "B")])

    result = _handler(path).handle(RebuildProjectionCommand("source_documents"))

    assert result.events_replayed == 2
    assert result.last_sequence == 2
    assert result.state["documents"][0]["title"] == "New"


def test_rebuild_persists_version_and_checkpoint(tmp_path) -> None:
    path = tmp_path / "events.db"
    SQLiteEventStore(path).append([_event("page-1", "Document", "A")])

    _handler(path).handle(RebuildProjectionCommand("source_documents"))
    snapshot = SQLiteProjectionStore(path).load("source_documents")

    assert snapshot is not None
    assert snapshot["version"] == 1
    assert snapshot["last_sequence"] == 1
    assert snapshot["state"]["statistics"] == {"documents": 1}


def test_same_history_produces_same_projection_state(tmp_path) -> None:
    first_path = tmp_path / "first.db"
    second_path = tmp_path / "second.db"
    events = [_event("page-2", "Beta", "B"), _event("page-1", "Alpha", "A")]
    SQLiteEventStore(first_path).append(events)
    SQLiteEventStore(second_path).append(events)

    first = _handler(first_path).handle(RebuildProjectionCommand("source_documents"))
    second = _handler(second_path).handle(RebuildProjectionCommand("source_documents"))

    assert first.state == second.state


def test_empty_stream_builds_empty_projection(tmp_path) -> None:
    path = tmp_path / "events.db"

    result = _handler(path).handle(RebuildProjectionCommand("source_documents"))

    assert result.events_replayed == 0
    assert result.last_sequence == 0
    assert result.state["statistics"] == {"documents": 0}


def test_registry_rejects_unknown_projection() -> None:
    registry = ProjectionRegistry([SourceDocumentProjection()])

    try:
        registry.get("missing")
    except ValueError as exc:
        assert "source_documents" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
