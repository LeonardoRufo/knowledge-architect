import pytest

from knowledge_architect.kir import EntityId, KnowledgeUnitId


def test_typed_identity_factory_uses_type_prefix() -> None:
    entity_id = EntityId.new()
    knowledge_unit_id = KnowledgeUnitId.new()

    assert str(entity_id).startswith("entity:")
    assert str(knowledge_unit_id).startswith("knowledge-unit:")
    assert entity_id != knowledge_unit_id


def test_identity_rejects_wrong_prefix() -> None:
    with pytest.raises(ValueError, match="must start"):
        EntityId("knowledge-unit:123e4567-e89b-12d3-a456-426614174000")


def test_identity_rejects_invalid_uuid() -> None:
    with pytest.raises(ValueError, match="UUID"):
        EntityId("entity:not-a-uuid")
