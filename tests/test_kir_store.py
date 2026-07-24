from dataclasses import FrozenInstanceError

import pytest

from knowledge_architect.kir import (
    Children,
    DuplicateIdentityError,
    Entity,
    EntityId,
    EntityNotFoundError,
    Equals,
    InMemoryKnowledgeStore,
    KindIs,
    KnowledgeStore,
    KnowledgeUnit,
    KnowledgeUnitId,
    KnowledgeUnitKind,
    Ordering,
    Projection,
    Query,
    Relation,
    RelationEndpoint,
    RelationId,
    RelationTargetKind,
    StoreCapabilities,
    StoreConflictPolicy,
    StoreResult,
    TransactionError,
    canonical_json,
)


def entity(label: str = "Cell") -> Entity:
    return Entity(EntityId.new(), "concept", label)


def test_store_port_and_capabilities_are_backend_independent() -> None:
    store = InMemoryKnowledgeStore()
    assert isinstance(store, KnowledgeStore)
    assert store.capabilities == StoreCapabilities(transactions=True, traversals=True)
    assert StoreConflictPolicy.REJECT.value == "reject"
    with pytest.raises(TypeError):
        KnowledgeStore()


def test_save_load_exists_list_count_and_clear() -> None:
    store = InMemoryKnowledgeStore()
    second = entity("B")
    first = entity("A")

    result = store.save(second)
    store.save(first)

    assert result.entity is second
    assert result.statistic("created") == 1
    assert store.load(first.id) is first
    assert store.exists(second.id)
    assert store.count() == 2
    assert store.list() == tuple(sorted((first, second), key=lambda item: str(item.id)))

    cleared = store.clear()
    assert cleared.statistic("deleted") == 2
    assert store.list() == ()


def test_conflicts_are_explicit_and_save_many_is_atomic_for_reject() -> None:
    store = InMemoryKnowledgeStore()
    original = entity("Original")
    replacement = Entity(original.id, "concept", "Replacement")
    store.save(original)

    with pytest.raises(DuplicateIdentityError):
        store.save(replacement)
    assert store.load(original.id) is original

    replaced = store.save(replacement, conflict_policy=StoreConflictPolicy.REPLACE)
    assert replaced.statistic("replaced") == 1
    assert store.load(original.id) is replacement

    new = entity("New")
    with pytest.raises(DuplicateIdentityError):
        store.save_many((new, replacement))
    assert not store.exists(new.id)


def test_delete_and_missing_identity_errors() -> None:
    store = InMemoryKnowledgeStore()
    item = entity()
    store.save(item)
    assert store.delete(item.id).entity is item
    with pytest.raises(EntityNotFoundError):
        store.load(item.id)
    with pytest.raises(EntityNotFoundError):
        store.delete(item.id)


def test_persistence_preserves_entity_and_canonical_serialization() -> None:
    store = InMemoryKnowledgeStore()
    item = entity()
    before = canonical_json(item)
    store.save(item)
    loaded = store.load(item.id)

    assert loaded is item
    assert canonical_json(loaded) == before
    with pytest.raises(FrozenInstanceError):
        loaded.label = "Changed"  # type: ignore[misc]


def test_query_filters_orders_projects_and_paginates_deterministically() -> None:
    store = InMemoryKnowledgeStore()
    items = (entity("Gamma"), entity("Alpha"), entity("Beta"))
    store.save_many(items)

    query = Query(
        predicate=KindIs("entity"),
        ordering=(Ordering("label"),),
        projection=Projection(("identity", "label")),
    ).paginate(offset=1, limit=1)
    result = store.query(query)

    assert result.elements == (
        (("identity", items[2].id.value), ("label", "Beta")),
    )
    assert result.metadata_value("backend") == "memory"
    assert result.statistic("matched") == 3
    assert result.statistic("returned") == 1


def test_query_equals_and_directed_children_traversal() -> None:
    store = InMemoryKnowledgeStore()
    parent = entity("Parent")
    child = entity("Child")
    relation = Relation(
        RelationId.new(),
        "contains",
        RelationEndpoint(RelationTargetKind.ENTITY, parent.id),
        RelationEndpoint(RelationTargetKind.ENTITY, child.id),
    )
    store.save_many((parent, child, relation))

    by_label = store.query(Query(predicate=Equals("label", "Child")))
    descendants = store.query(Query(origin=(parent.id,), traversal=Children()))

    assert by_label.elements == (child,)
    assert descendants.elements == (child,)


def test_transaction_commits_and_rolls_back_atomically() -> None:
    store = InMemoryKnowledgeStore()
    first = entity("First")
    second = entity("Second")

    transaction = store.transaction()
    transaction.save(first)
    transaction.save(second)
    results = transaction.commit()
    assert len(results) == 2
    assert store.count() == 2
    with pytest.raises(TransactionError):
        transaction.commit()

    duplicate = Entity(first.id, "concept", "Duplicate")
    transaction = store.transaction()
    transaction.delete(second.id)
    transaction.save(duplicate)
    with pytest.raises(TransactionError):
        transaction.commit()
    assert store.exists(second.id)
    assert store.load(first.id) is first


def test_store_result_is_immutable_and_deterministic() -> None:
    result = StoreResult(metadata=(("operation", "save"), ("backend", "memory")))
    assert result.metadata == (("backend", "memory"), ("operation", "save"))
    assert canonical_json(result).startswith('{"entity":null,"metadata":')
    with pytest.raises(FrozenInstanceError):
        result.entity = entity()  # type: ignore[misc]
    with pytest.raises(ValueError, match="unique"):
        StoreResult(metadata=(("key", "a"), ("key", "b")))


def test_store_accepts_other_canonical_kir_objects() -> None:
    store = InMemoryKnowledgeStore()
    unit = KnowledgeUnit(
        KnowledgeUnitId.new(), KnowledgeUnitKind.ASSERTION, "Cells have membranes."
    )
    store.save(unit)
    assert store.load(unit.id) is unit
