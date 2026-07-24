from datetime import UTC, datetime

from knowledge_architect.kir import (
    Entity,
    EntityId,
    Provenance,
    ProvenanceId,
    ProvenanceKind,
    canonical_json,
    to_primitive,
)


def test_serialization_converts_typed_values_to_primitives() -> None:
    entity = Entity(
        id=EntityId("entity:123e4567-e89b-12d3-a456-426614174000"),
        kind="person",
        label="Ada",
        aliases=("A. Lovelace",),
    )

    assert to_primitive(entity) == {
        "id": "entity:123e4567-e89b-12d3-a456-426614174000",
        "kind": "person",
        "label": "Ada",
        "aliases": ["A. Lovelace"],
    }


def test_canonical_json_is_deterministic() -> None:
    provenance = Provenance(
        id=ProvenanceId("provenance:123e4567-e89b-12d3-a456-426614174000"),
        kind=ProvenanceKind.OBSERVED,
        agent="connector",
        occurred_at=datetime(2026, 7, 24, 20, tzinfo=UTC),
        source_refs=("source:b", "source:a"),
    )

    first = canonical_json(provenance)
    second = canonical_json(provenance)

    assert first == second
    assert first == (
        '{"agent":"connector","id":"provenance:123e4567-e89b-12d3-a456-426614174000",'
        '"kind":"observed","occurred_at":"2026-07-24T20:00:00+00:00",'
        '"source_refs":["source:b","source:a"]}'
    )
