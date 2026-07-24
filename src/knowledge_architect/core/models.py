from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class KnowledgeEvent(BaseModel):
    """Immutable event emitted by a connector or a future reasoning component."""

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: str
    source_system: str
    source_id: str
    logical_time: int = 0
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
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
