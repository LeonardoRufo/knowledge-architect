from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from knowledge_architect.core.models import KnowledgeEvent


class StoredEvent(BaseModel):
    """Event plus its stable position in the persisted stream."""

    model_config = ConfigDict(frozen=True)

    sequence: int = Field(ge=1)
    event: KnowledgeEvent
