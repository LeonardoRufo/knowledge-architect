from knowledge_architect.application import SyncSourceArtifactCommand, SyncSourceArtifactHandler
from knowledge_architect.core import SourceDocument, SourceObservationEventFactory
from knowledge_architect.event_store import SQLiteEventStore


class StubSourceProvider:
    def __init__(self, content: str = "# Conteúdo") -> None:
        self.content = content

    def fetch(self, source_id: str) -> SourceDocument:
        return SourceDocument(
            source_system="stub",
            source_id=source_id,
            title="Documento de teste",
            content_markdown=self.content,
        )


def test_handler_orchestrates_sync_through_ports(tmp_path) -> None:
    store = SQLiteEventStore(tmp_path / "events.sqlite3")
    provider = StubSourceProvider()
    handler = SyncSourceArtifactHandler(
        source_provider=provider,
        event_store=store,
        event_factory=SourceObservationEventFactory(),
    )

    result = handler.handle(SyncSourceArtifactCommand(source_id="source-1"))

    assert result.inserted == 1
    assert result.source_system == "stub"
    assert result.source_id == "source-1"
    assert result.title == "Documento de teste"
    assert store.count() == 1


def test_repeated_sync_is_idempotent_until_content_changes(tmp_path) -> None:
    store = SQLiteEventStore(tmp_path / "events.sqlite3")
    provider = StubSourceProvider("Version 1")
    handler = SyncSourceArtifactHandler(
        source_provider=provider,
        event_store=store,
        event_factory=SourceObservationEventFactory(),
    )
    command = SyncSourceArtifactCommand(source_id="source-1")

    first = handler.handle(command)
    repeated = handler.handle(command)
    provider.content = "Version 2"
    changed = handler.handle(command)

    assert first.inserted == 1
    assert repeated.inserted == 0
    assert changed.inserted == 1
    assert store.count() == 2
