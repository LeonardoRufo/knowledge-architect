from datetime import UTC, datetime

from knowledge_architect.core import (
    SourceDocument,
    SourceObservationEventFactory,
    content_fingerprint,
    normalize_markdown,
    observe_source_document,
)


def document(content: str = "# Title\n\nBody") -> SourceDocument:
    return SourceDocument(
        source_system="notion",
        source_id="page-1",
        title="Title",
        content_markdown=content,
        raw_metadata={"archived": False},
    )


def test_markdown_normalization_ignores_line_endings_and_trailing_whitespace() -> None:
    first = "# Title\r\n\r\nBody   \r\n"
    second = "# Title\n\nBody"

    assert normalize_markdown(first) == normalize_markdown(second)
    assert content_fingerprint(document(first)) == content_fingerprint(document(second))


def test_equivalent_observations_have_distinct_occurrences_but_same_identity() -> None:
    observed_at = datetime(2026, 7, 24, tzinfo=UTC)
    first = observe_source_document(document(), observed_at=observed_at)
    second = observe_source_document(document(), observed_at=observed_at)

    assert first.observation_id != second.observation_id
    assert first.content_fingerprint == second.content_fingerprint
    assert first.idempotency_key == second.idempotency_key


def test_content_change_creates_new_logical_observation() -> None:
    first = observe_source_document(document("Version 1"))
    second = observe_source_document(document("Version 2"))

    assert first.content_fingerprint != second.content_fingerprint
    assert first.idempotency_key != second.idempotency_key


def test_event_factory_preserves_occurrence_and_idempotency_identity() -> None:
    factory = SourceObservationEventFactory()

    first = factory(document())
    second = factory(document())

    assert first.event_id != second.event_id
    assert first.content_fingerprint == second.content_fingerprint
    assert first.idempotency_key == second.idempotency_key
