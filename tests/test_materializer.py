from knowledge_architect.core import KnowledgeEvent
from knowledge_architect.materializer import materialize


def test_materializer_uses_latest_observation() -> None:
    events = [
        KnowledgeEvent(
            event_type="source_document_observed",
            source_system="notion",
            source_id="page-1",
            payload={"title": "Antigo", "content_markdown": "A"},
        ),
        KnowledgeEvent(
            event_type="source_document_observed",
            source_system="notion",
            source_id="page-1",
            payload={"title": "Novo", "content_markdown": "B"},
        ),
    ]
    state = materialize(events)
    assert state["statistics"]["documents"] == 1
    assert state["documents"][0]["title"] == "Novo"
