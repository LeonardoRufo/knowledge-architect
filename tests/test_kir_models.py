from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from knowledge_architect.kir import (
    Entity,
    EntityId,
    Evidence,
    EvidenceId,
    EvidenceKind,
    KnowledgeUnit,
    KnowledgeUnitId,
    KnowledgeUnitKind,
    Provenance,
    ProvenanceId,
    ProvenanceKind,
    Relation,
    RelationEndpoint,
    RelationId,
    RelationTargetKind,
)


def test_entity_is_immutable_and_validates_aliases() -> None:
    entity = Entity(EntityId.new(), kind="person", label="Ada", aliases=("A. Lovelace",))

    with pytest.raises(FrozenInstanceError):
        entity.label = "Changed"  # type: ignore[misc]

    with pytest.raises(ValueError, match="unique"):
        Entity(EntityId.new(), kind="person", label="Ada", aliases=("Ada", "Ada"))


def test_knowledge_unit_links_typed_subject_evidence_and_provenance() -> None:
    entity_id = EntityId.new()
    evidence_id = EvidenceId.new()
    provenance_id = ProvenanceId.new()

    unit = KnowledgeUnit(
        id=KnowledgeUnitId.new(),
        kind=KnowledgeUnitKind.ASSERTION,
        content="Ada designed an analytical engine algorithm.",
        subject_ids=(entity_id,),
        evidence_ids=(evidence_id,),
        provenance_id=provenance_id,
    )

    assert unit.subject_ids == (entity_id,)
    assert unit.evidence_ids == (evidence_id,)
    assert unit.provenance_id == provenance_id


def test_knowledge_unit_rejects_empty_content_and_duplicate_links() -> None:
    entity_id = EntityId.new()

    with pytest.raises(ValueError, match="content"):
        KnowledgeUnit(KnowledgeUnitId.new(), KnowledgeUnitKind.ASSERTION, " ")

    with pytest.raises(ValueError, match="subject_ids"):
        KnowledgeUnit(
            KnowledgeUnitId.new(),
            KnowledgeUnitKind.ASSERTION,
            "Statement",
            subject_ids=(entity_id, entity_id),
        )


def test_relation_requires_endpoint_id_matching_target_kind() -> None:
    with pytest.raises(TypeError, match="EntityId"):
        RelationEndpoint(RelationTargetKind.ENTITY, KnowledgeUnitId.new())


def test_relation_rejects_self_relation() -> None:
    entity_id = EntityId.new()
    endpoint = RelationEndpoint(RelationTargetKind.ENTITY, entity_id)

    with pytest.raises(ValueError, match="self-relations"):
        Relation(RelationId.new(), "same_as", endpoint, endpoint)


def test_evidence_validates_source_fields() -> None:
    evidence = Evidence(
        id=EvidenceId.new(),
        kind=EvidenceKind.SOURCE_EXCERPT,
        source_system="notion",
        source_id="page-1",
        content="Quoted source text",
        locator="block-4",
    )

    assert evidence.source_id == "page-1"

    with pytest.raises(ValueError, match="source_id"):
        Evidence(EvidenceId.new(), EvidenceKind.OBSERVATION, "notion", "", "Observed")


def test_provenance_normalizes_time_to_utc_and_rejects_naive_time() -> None:
    provenance = Provenance(
        id=ProvenanceId.new(),
        kind=ProvenanceKind.OBSERVED,
        agent="notion-connector",
        occurred_at=datetime(2026, 7, 24, 20, tzinfo=UTC),
        source_refs=("notion:page-1",),
    )

    assert provenance.occurred_at.tzinfo is UTC

    with pytest.raises(ValueError, match="timezone-aware"):
        Provenance(
            ProvenanceId.new(),
            ProvenanceKind.AUTHORED,
            "human",
            datetime(2026, 7, 24),  # noqa: DTZ001
        )
