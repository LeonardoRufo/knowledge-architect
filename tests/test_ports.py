from collections.abc import Iterable

from knowledge_architect.core import KnowledgeEvent, SourceDocument
from knowledge_architect.event_store import SQLiteEventStore
from knowledge_architect.ports import EventFactoryPort, EventStorePort, SourceProviderPort


class Provider:
    def fetch(self, source_id: str) -> SourceDocument:
        return SourceDocument(
            source_system="test",
            source_id=source_id,
            title="Test",
            content_markdown="",
        )


class Factory:
    def __call__(self, document: SourceDocument) -> KnowledgeEvent:
        return KnowledgeEvent(
            event_type="source_document_observed",
            source_system=document.source_system,
            source_id=document.source_id,
        )


def accepts_source_provider(port: SourceProviderPort) -> None:
    port.fetch("source")


def accepts_event_store(port: EventStorePort, events: Iterable[KnowledgeEvent]) -> None:
    port.append(events)


def accepts_event_factory(port: EventFactoryPort, document: SourceDocument) -> None:
    port(document)


def test_existing_adapters_satisfy_port_shapes(tmp_path) -> None:
    provider = Provider()
    factory = Factory()
    store = SQLiteEventStore(tmp_path / "events.sqlite3")
    document = provider.fetch("source")
    event = factory(document)

    accepts_source_provider(provider)
    accepts_event_store(store, [event])
    accepts_event_factory(factory, document)

    assert store.count() == 1
