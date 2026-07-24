from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from .identity import ProvenanceId


class ProvenanceKind(StrEnum):
    OBSERVED = "observed"
    AUTHORED = "authored"
    IMPORTED = "imported"
    DERIVED = "derived"


@dataclass(frozen=True, slots=True)
class Provenance:
    """Origin metadata for a KIR Core object."""

    id: ProvenanceId
    kind: ProvenanceKind
    agent: str
    occurred_at: datetime
    source_refs: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.agent.strip():
            raise ValueError("agent must not be empty")
        if self.occurred_at.tzinfo is None or self.occurred_at.utcoffset() is None:
            raise ValueError("occurred_at must be timezone-aware")
        if any(not ref.strip() for ref in self.source_refs):
            raise ValueError("source_refs must not contain empty values")
        if len(set(self.source_refs)) != len(self.source_refs):
            raise ValueError("source_refs must be unique")
        object.__setattr__(self, "occurred_at", self.occurred_at.astimezone(UTC))
