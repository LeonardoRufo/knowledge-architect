from knowledge_architect.core import KnowledgeEvent
from knowledge_architect.event_store import SQLiteEventStore


def test_list_stream_exposes_stable_sequences_and_cursor(tmp_path) -> None:
    store = SQLiteEventStore(tmp_path / "events.db")
    store.append(
        [
            KnowledgeEvent(event_type="one", source_system="test", source_id="1"),
            KnowledgeEvent(event_type="two", source_system="test", source_id="2"),
        ]
    )

    assert [item.sequence for item in store.list_stream()] == [1, 2]
    assert [item.event.event_type for item in store.list_stream(after_sequence=1)] == ["two"]
