import sqlite3

from knowledge_architect.core import KnowledgeEvent, SourceDocument, SourceObservationEventFactory
from knowledge_architect.event_store import SQLiteEventStore


def test_store_deduplicates_same_occurrence_by_event_id(tmp_path) -> None:
    store = SQLiteEventStore(tmp_path / "events.sqlite3")
    event = KnowledgeEvent(
        event_type="source_document_observed",
        source_system="notion",
        source_id="page-1",
    )

    assert store.append([event]) == 1
    assert store.append([event]) == 0
    assert store.count() == 1


def test_store_deduplicates_equivalent_events_by_idempotency_key(tmp_path) -> None:
    store = SQLiteEventStore(tmp_path / "events.sqlite3")
    document = SourceDocument(
        source_system="notion",
        source_id="page-1",
        title="Title",
        content_markdown="Same content",
    )
    factory = SourceObservationEventFactory()
    first = factory(document)
    second = factory(document)

    assert first.event_id != second.event_id
    assert store.append([first]) == 1
    assert store.append([second]) == 0
    assert store.count() == 1
    assert store.list_events()[0].event_id == first.event_id


def test_store_accepts_changed_content_as_new_event(tmp_path) -> None:
    store = SQLiteEventStore(tmp_path / "events.sqlite3")
    factory = SourceObservationEventFactory()
    first = factory(
        SourceDocument(
            source_system="notion",
            source_id="page-1",
            title="Title",
            content_markdown="Version 1",
        )
    )
    second = factory(
        SourceDocument(
            source_system="notion",
            source_id="page-1",
            title="Title",
            content_markdown="Version 2",
        )
    )

    assert store.append([first, second]) == 2
    assert store.count() == 2


def test_store_migrates_database_created_before_rfc_003(tmp_path) -> None:
    path = tmp_path / "events.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE events (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL UNIQUE,
                event_type TEXT NOT NULL,
                source_system TEXT NOT NULL,
                source_id TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                event_json TEXT NOT NULL
            )
            """
        )

    store = SQLiteEventStore(path)
    event = SourceObservationEventFactory()(
        SourceDocument(
            source_system="notion",
            source_id="page-1",
            title="Title",
            content_markdown="Content",
        )
    )

    assert store.append([event]) == 1
    assert store.count() == 1
