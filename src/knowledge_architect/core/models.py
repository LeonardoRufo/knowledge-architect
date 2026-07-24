from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeEvent(BaseModel):
    """Immutable fact stored in the event stream.

    ``event_id`` identifies one concrete occurrence. ``idempotency_key``
    identifies the logical fact so equivalent observations can be ignored by
    the event store without erasing occurrence identity.
    """

    model_config = ConfigDict(frozen=True)

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: str
    source_system: str
    source_id: str
    idempotency_key: str | None = None
    content_fingerprint: str | None = None
    logical_time: int = 0
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    causation_ids: list[str] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)


class SourceDocument(BaseModel):
    """Normalized source document before semantic extraction."""

    source_system: str
    source_id: str
    title: str
    url: str | None = None
    last_edited_time: datetime | None = None
    content_markdown: str
    raw_metadata: dict[str, Any] = Field(default_factory=dict)


class SourceObservation(BaseModel):
    """A point-in-time observation of one normalized source document."""

    model_config = ConfigDict(frozen=True)

    observation_id: str = Field(default_factory=lambda: str(uuid4()))
    source_system: str
    source_id: str
    observed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    content_fingerprint: str
    idempotency_key: str
    document: SourceDocument
