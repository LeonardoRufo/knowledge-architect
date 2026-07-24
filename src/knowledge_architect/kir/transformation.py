from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from .identity import KnowledgeUnitId, ProvenanceId, RelationId, TransformationId
from .knowledge_unit import KnowledgeUnit
from .provenance import Provenance
from .relation import Relation


class TransformationKind(StrEnum):
    MERGE = "merge"
    SPLIT = "split"
    REFORMULATION = "reformulation"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"
    NORMALIZATION = "normalization"
    EXTRACTION = "extraction"


class RelationTransformationOutcome(StrEnum):
    PRESERVED = "preserved"
    COPIED = "copied"
    REFORMULATED = "reformulated"
    OMITTED = "omitted"
    NOT_APPLICABLE = "not_applicable"
    REQUIRES_REVIEW = "requires_review"


@dataclass(frozen=True, slots=True)
class TransformationMapping:
    """Explicit semantic correspondence between source and target units."""

    source_ids: tuple[KnowledgeUnitId, ...]
    target_ids: tuple[KnowledgeUnitId, ...]
    rationale: str = ""

    def __post_init__(self) -> None:
        if not self.source_ids:
            raise ValueError("source_ids must not be empty")
        if not self.target_ids:
            raise ValueError("target_ids must not be empty")
        if len(set(self.source_ids)) != len(self.source_ids):
            raise ValueError("source_ids must be unique")
        if len(set(self.target_ids)) != len(self.target_ids):
            raise ValueError("target_ids must be unique")
        if set(self.source_ids) & set(self.target_ids):
            raise ValueError("source and target identities must be distinct")


@dataclass(frozen=True, slots=True)
class RelationTransformationDecision:
    """Declared handling of one relation affected by a transformation."""

    source_relation_id: RelationId
    outcome: RelationTransformationOutcome
    target_relation_ids: tuple[RelationId, ...] = field(default_factory=tuple)
    rationale: str = ""

    def __post_init__(self) -> None:
        if len(set(self.target_relation_ids)) != len(self.target_relation_ids):
            raise ValueError("target_relation_ids must be unique")
        requires_targets = {
            RelationTransformationOutcome.COPIED,
            RelationTransformationOutcome.REFORMULATED,
        }
        forbids_targets = {
            RelationTransformationOutcome.PRESERVED,
            RelationTransformationOutcome.OMITTED,
            RelationTransformationOutcome.NOT_APPLICABLE,
            RelationTransformationOutcome.REQUIRES_REVIEW,
        }
        if self.outcome in requires_targets and not self.target_relation_ids:
            raise ValueError(f"{self.outcome.value} decisions require target_relation_ids")
        if self.outcome in forbids_targets and self.target_relation_ids:
            raise ValueError(f"{self.outcome.value} decisions cannot define target_relation_ids")


@dataclass(frozen=True, slots=True)
class RelationTransformationPolicy:
    """Complete declarative record of relation handling for a transformation."""

    decisions: tuple[RelationTransformationDecision, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        relation_ids = tuple(decision.source_relation_id for decision in self.decisions)
        if len(set(relation_ids)) != len(relation_ids):
            raise ValueError("each source relation must have exactly one decision")

    def decision_for(self, relation_id: RelationId) -> RelationTransformationDecision:
        for decision in self.decisions:
            if decision.source_relation_id == relation_id:
                return decision
        raise KeyError(f"no transformation decision for relation {relation_id}")


@dataclass(frozen=True, slots=True)
class KnowledgeUnitTransformation:
    """Immutable first-class record of semantic KnowledgeUnit evolution."""

    id: TransformationId
    kind: TransformationKind
    mappings: tuple[TransformationMapping, ...]
    provenance_id: ProvenanceId
    relation_policy: RelationTransformationPolicy = field(
        default_factory=RelationTransformationPolicy
    )
    description: str = ""

    def __post_init__(self) -> None:
        if not self.mappings:
            raise ValueError("mappings must not be empty")

        sources = tuple(source for mapping in self.mappings for source in mapping.source_ids)
        targets = tuple(target for mapping in self.mappings for target in mapping.target_ids)
        if len(set(sources)) != len(sources):
            raise ValueError("source identities must occur in exactly one mapping")
        if len(set(targets)) != len(targets):
            raise ValueError("target identities must occur in exactly one mapping")
        if set(sources) & set(targets):
            raise ValueError("transformations must create new target identities")

        expected_shape = {
            TransformationKind.MERGE: (lambda: len(sources) > 1 and len(targets) == 1),
            TransformationKind.SPLIT: (lambda: len(sources) == 1 and len(targets) > 1),
        }
        validator = expected_shape.get(self.kind)
        if validator is not None and not validator():
            raise ValueError(f"invalid source/target shape for {self.kind.value}")

    @property
    def source_ids(self) -> tuple[KnowledgeUnitId, ...]:
        return tuple(source for mapping in self.mappings for source in mapping.source_ids)

    @property
    def target_ids(self) -> tuple[KnowledgeUnitId, ...]:
        return tuple(target for mapping in self.mappings for target in mapping.target_ids)


@dataclass(frozen=True, slots=True)
class TransformationResult:
    """Validated bundle of a transformation and the immutable objects it created."""

    transformation: KnowledgeUnitTransformation
    created_units: tuple[KnowledgeUnit, ...]
    provenance: Provenance
    created_relations: tuple[Relation, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        unit_ids = tuple(unit.id for unit in self.created_units)
        if len(set(unit_ids)) != len(unit_ids):
            raise ValueError("created unit identities must be unique")
        if set(unit_ids) != set(self.transformation.target_ids):
            raise ValueError("created_units must exactly match transformation target_ids")
        if self.provenance.id != self.transformation.provenance_id:
            raise ValueError("provenance must match transformation provenance_id")

        relation_ids = tuple(relation.id for relation in self.created_relations)
        if len(set(relation_ids)) != len(relation_ids):
            raise ValueError("created relation identities must be unique")

        declared_relation_ids = {
            target_id
            for decision in self.transformation.relation_policy.decisions
            for target_id in decision.target_relation_ids
        }
        if set(relation_ids) != declared_relation_ids:
            raise ValueError(
                "created_relations must exactly match relation policy target_relation_ids"
            )
