from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .identity import EntityId, KnowledgeUnitId, RelationId


class RelationTargetKind(StrEnum):
    ENTITY = "entity"
    KNOWLEDGE_UNIT = "knowledge_unit"


@dataclass(frozen=True, slots=True)
class RelationEndpoint:
    kind: RelationTargetKind
    id: EntityId | KnowledgeUnitId

    def __post_init__(self) -> None:
        expected_type = EntityId if self.kind is RelationTargetKind.ENTITY else KnowledgeUnitId
        if not isinstance(self.id, expected_type):
            raise TypeError(f"{self.kind.value} endpoint requires {expected_type.__name__}")


@dataclass(frozen=True, slots=True)
class Relation:
    """Explicit directed relation between two KIR Core objects."""

    id: RelationId
    relation_type: str
    source: RelationEndpoint
    target: RelationEndpoint

    def __post_init__(self) -> None:
        if not self.relation_type.strip():
            raise ValueError("relation_type must not be empty")
        if self.source == self.target:
            raise ValueError("self-relations are not allowed in the KIR Core")
