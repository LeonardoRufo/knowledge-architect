from datetime import UTC, datetime

from knowledge_architect.application import SyncSourceArtifactCommand, SyncSourceArtifactHandler
from knowledge_architect.core import KnowledgeEvent, SourceDocument
from knowledge_architect.event_store import SQLiteEventStore


class StubSourceProvider:
    def fetch(self, source_id: str) -> SourceDocument:
        return SourceDocument(
            source_system="stub",
            source_id=source_id,
            title="Documento de teste",
            content_markdown="# Conteúdo",
        )


def stub_event_factory(document: SourceDocument) -> KnowledgeEvent:
    return KnowledgeEvent(
        event_id="event-1",
        event_type="source_document_observed",
        source_system=document.source_system,
        source_id=document.source_id,
        occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
        payload={"title": document.title, "content_markdown": document.content_markdown},
    )


def test_handler_orchestrates_sync_through_ports(tmp_path) -> None:
    store = SQLiteEventStore(tmp_path / "events.sqlite3")
    provider = StubSourceProvider()
    handler = SyncSourceArtifactHandler(
        source_provider=provider,
        event_store=store,
        event_factory=stub_event_factory,
    )

    result = handler.handle(SyncSourceArtifactCommand(source_id="source-1"))

    assert result.inserted == 1
    assert result.source_system == "stub"
    assert result.source_id == "source-1"
    assert result.title == "Documento de teste"
    assert store.count() == 1
