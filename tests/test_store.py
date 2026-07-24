from knowledge_architect.core import KnowledgeEvent
from knowledge_architect.event_store import SQLiteEventStore


def test_store_appends_and_reads(tmp_path) -> None:
    store = SQLiteEventStore(tmp_path / "events.sqlite3")
    event = KnowledgeEvent(
        event_type="source_document_observed",
        source_system="notion",
        source_id="page-1",
    )
    assert store.append([event]) == 1
    assert store.append([event]) == 0
    assert store.count() == 1
    assert store.list_events()[0].event_id == event.event_id
