from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from knowledge_architect.kir import (
    KnowledgeUnit,
    KnowledgeUnitId,
    KnowledgeUnitKind,
    KnowledgeUnitTransformation,
    Provenance,
    ProvenanceId,
    ProvenanceKind,
    RelationId,
    RelationTransformationDecision,
    RelationTransformationOutcome,
    RelationTransformationPolicy,
    TransformationId,
    TransformationKind,
    TransformationMapping,
    TransformationResult,
    canonical_json,
)


def _id(number: int) -> KnowledgeUnitId:
    return KnowledgeUnitId(f"knowledge-unit:123e4567-e89b-12d3-a456-{number:012d}")


def _provenance() -> Provenance:
    return Provenance(
        id=ProvenanceId("provenance:123e4567-e89b-12d3-a456-426614174000"),
        kind=ProvenanceKind.DERIVED,
        agent="knowledge-architect",
        occurred_at=datetime(2026, 7, 24, tzinfo=UTC),
    )


def test_merge_records_new_identity_and_explicit_mapping() -> None:
    transformation = KnowledgeUnitTransformation(
        id=TransformationId.new(),
        kind=TransformationKind.MERGE,
        mappings=(TransformationMapping((_id(1), _id(2)), (_id(3),)),),
        provenance_id=_provenance().id,
    )

    assert transformation.source_ids == (_id(1), _id(2))
    assert transformation.target_ids == (_id(3),)
    assert set(transformation.source_ids).isdisjoint(transformation.target_ids)


def test_split_requires_one_source_and_multiple_targets() -> None:
    valid = KnowledgeUnitTransformation(
        id=TransformationId.new(),
        kind=TransformationKind.SPLIT,
        mappings=(TransformationMapping((_id(1),), (_id(2), _id(3))),),
        provenance_id=_provenance().id,
    )
    assert valid.target_ids == (_id(2), _id(3))

    with pytest.raises(ValueError, match="invalid source/target shape"):
        KnowledgeUnitTransformation(
            id=TransformationId.new(),
            kind=TransformationKind.SPLIT,
            mappings=(TransformationMapping((_id(1), _id(2)), (_id(3),)),),
            provenance_id=_provenance().id,
        )


def test_reformulation_is_first_class_and_immutable() -> None:
    transformation = KnowledgeUnitTransformation(
        id=TransformationId.new(),
        kind=TransformationKind.REFORMULATION,
        mappings=(TransformationMapping((_id(1),), (_id(2),), "Clarified wording"),),
        provenance_id=_provenance().id,
    )

    with pytest.raises(FrozenInstanceError):
        transformation.description = "changed"  # type: ignore[misc]


def test_mapping_rejects_reused_or_overlapping_identities() -> None:
    with pytest.raises(ValueError, match="distinct"):
        TransformationMapping((_id(1),), (_id(1),))

    with pytest.raises(ValueError, match="exactly one mapping"):
        KnowledgeUnitTransformation(
            id=TransformationId.new(),
            kind=TransformationKind.NORMALIZATION,
            mappings=(
                TransformationMapping((_id(1),), (_id(3),)),
                TransformationMapping((_id(1),), (_id(4),)),
            ),
            provenance_id=_provenance().id,
        )


def test_relation_policy_requires_one_explicit_decision_per_source_relation() -> None:
    relation_id = RelationId.new()
    decision = RelationTransformationDecision(
        relation_id,
        RelationTransformationOutcome.REQUIRES_REVIEW,
        rationale="Semantics may have changed.",
    )
    policy = RelationTransformationPolicy((decision,))

    assert policy.decision_for(relation_id) is decision
    with pytest.raises(KeyError, match="no transformation decision"):
        policy.decision_for(RelationId.new())
    with pytest.raises(ValueError, match="exactly one decision"):
        RelationTransformationPolicy((decision, decision))


def test_copied_and_reformulated_relations_require_new_relation_ids() -> None:
    for outcome in (
        RelationTransformationOutcome.COPIED,
        RelationTransformationOutcome.REFORMULATED,
    ):
        with pytest.raises(ValueError, match="require target_relation_ids"):
            RelationTransformationDecision(RelationId.new(), outcome)

    with pytest.raises(ValueError, match="cannot define target_relation_ids"):
        RelationTransformationDecision(
            RelationId.new(),
            RelationTransformationOutcome.OMITTED,
            (RelationId.new(),),
        )


def test_result_requires_created_units_to_match_declared_targets() -> None:
    provenance = _provenance()
    transformation = KnowledgeUnitTransformation(
        id=TransformationId.new(),
        kind=TransformationKind.REFORMULATION,
        mappings=(TransformationMapping((_id(1),), (_id(2),)),),
        provenance_id=provenance.id,
    )
    unit = KnowledgeUnit(_id(2), KnowledgeUnitKind.ASSERTION, "Reformulated")
    result = TransformationResult(transformation, (unit,), provenance)
    assert result.created_units == (unit,)

    wrong_unit = KnowledgeUnit(_id(3), KnowledgeUnitKind.ASSERTION, "Wrong")
    with pytest.raises(ValueError, match="exactly match"):
        TransformationResult(transformation, (wrong_unit,), provenance)


def test_result_requires_matching_provenance() -> None:
    provenance = _provenance()
    transformation = KnowledgeUnitTransformation(
        id=TransformationId.new(),
        kind=TransformationKind.EXTRACTION,
        mappings=(TransformationMapping((_id(1),), (_id(2),)),),
        provenance_id=provenance.id,
    )
    unit = KnowledgeUnit(_id(2), KnowledgeUnitKind.ASSERTION, "Extracted")
    other = Provenance(
        ProvenanceId.new(),
        ProvenanceKind.DERIVED,
        "other",
        datetime(2026, 7, 24, tzinfo=UTC),
    )

    with pytest.raises(ValueError, match="provenance must match"):
        TransformationResult(transformation, (unit,), other)


def test_transformation_serialization_is_deterministic() -> None:
    transformation = KnowledgeUnitTransformation(
        id=TransformationId("transformation:123e4567-e89b-12d3-a456-426614174000"),
        kind=TransformationKind.TRANSLATION,
        mappings=(TransformationMapping((_id(1),), (_id(2),), "pt-BR to en"),),
        provenance_id=ProvenanceId("provenance:123e4567-e89b-12d3-a456-426614174000"),
        description="English translation",
    )

    assert canonical_json(transformation) == (
        '{"description":"English translation",'
        '"id":"transformation:123e4567-e89b-12d3-a456-426614174000",'
        '"kind":"translation","mappings":[{"rationale":"pt-BR to en",'
        '"source_ids":["knowledge-unit:123e4567-e89b-12d3-a456-000000000001"],'
        '"target_ids":["knowledge-unit:123e4567-e89b-12d3-a456-000000000002"]}],'
        '"provenance_id":"provenance:123e4567-e89b-12d3-a456-426614174000",'
        '"relation_policy":{"decisions":[]}}'
    )
