from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from knowledge_architect.core.models import KnowledgeEvent, SourceDocument, SourceObservation

SOURCE_DOCUMENT_OBSERVED = "source_document_observed"


def normalize_markdown(content: str) -> str:
    """Return a stable representation for content-level comparison.

    Line endings are normalized, trailing horizontal whitespace is removed,
    and redundant blank lines at the end of the document are discarded.
    Meaningful leading whitespace and internal blank lines are preserved.
    """

    normalized_newlines = content.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip(" \t") for line in normalized_newlines.split("\n")]
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def content_fingerprint(document: SourceDocument) -> str:
    normalized_content = normalize_markdown(document.content_markdown)
    return _sha256(normalized_content)


def observation_idempotency_key(
    document: SourceDocument,
    fingerprint: str,
    *,
    event_type: str = SOURCE_DOCUMENT_OBSERVED,
) -> str:
    identity = {
        "event_type": event_type,
        "source_id": document.source_id,
        "source_system": document.source_system,
        "content_fingerprint": fingerprint,
    }
    canonical = json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return _sha256(canonical)


def observe_source_document(
    document: SourceDocument,
    *,
    observed_at: datetime | None = None,
) -> SourceObservation:
    fingerprint = content_fingerprint(document)
    return SourceObservation(
        source_system=document.source_system,
        source_id=document.source_id,
        observed_at=observed_at or datetime.now(UTC),
        content_fingerprint=fingerprint,
        idempotency_key=observation_idempotency_key(document, fingerprint),
        document=document,
    )


class SourceObservationEventFactory:
    """Translate source documents into deterministic, idempotent events."""

    def __call__(self, document: SourceDocument) -> KnowledgeEvent:
        observation = observe_source_document(document)
        return KnowledgeEvent(
            event_type=SOURCE_DOCUMENT_OBSERVED,
            source_system=observation.source_system,
            source_id=observation.source_id,
            idempotency_key=observation.idempotency_key,
            content_fingerprint=observation.content_fingerprint,
            occurred_at=observation.observed_at,
            payload=_event_payload(observation.document),
        )


def _event_payload(document: SourceDocument) -> dict[str, Any]:
    return {
        "title": document.title,
        "url": document.url,
        "last_edited_time": (
            document.last_edited_time.isoformat() if document.last_edited_time else None
        ),
        "content_markdown": document.content_markdown,
        "content_sha256": content_fingerprint(document),
        "metadata": document.raw_metadata,
    }


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
