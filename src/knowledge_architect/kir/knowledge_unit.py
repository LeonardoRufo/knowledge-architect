from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from .identity import EntityId, EvidenceId, KnowledgeUnitId, ProvenanceId


class KnowledgeUnitKind(StrEnum):
    ASSERTION = "assertion"
    DEFINITION = "definition"
    QUESTION = "question"
    PROCEDURE = "procedure"
    DECISION = "decision"


@dataclass(frozen=True, slots=True)
class KnowledgeUnit:
    """Atomic immutable semantic statement in the KIR Core."""

    id: KnowledgeUnitId
    kind: KnowledgeUnitKind
    content: str
    subject_ids: tuple[EntityId, ...] = field(default_factory=tuple)
    evidence_ids: tuple[EvidenceId, ...] = field(default_factory=tuple)
    provenance_id: ProvenanceId | None = None

    def __post_init__(self) -> None:
        if not self.content.strip():
            raise ValueError("content must not be empty")
        if len(set(self.subject_ids)) != len(self.subject_ids):
            raise ValueError("subject_ids must be unique")
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("evidence_ids must be unique")
