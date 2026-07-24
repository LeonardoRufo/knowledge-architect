from dataclasses import FrozenInstanceError

import pytest

from knowledge_architect.kir import (
    And,
    Entity,
    EntityId,
    Equals,
    ExtensionDefinition,
    ExtensionId,
    IndexCapabilities,
    IndexManager,
    IndexResult,
    IndexStatistics,
    InMemoryKnowledgeStore,
    InMemorySearchIndex,
    KindIs,
    NamespaceIs,
    NotEquals,
    Or,
    Query,
    SearchIndex,
    canonical_json,
)


def entity(label: str, kind: str = "concept") -> Entity:
    return Entity(EntityId.new(), kind, label)


def indexed_store() -> tuple[InMemoryKnowledgeStore, IndexManager, InMemorySearchIndex]:
    store = InMemoryKnowledgeStore()
    index = InMemorySearchIndex()
    manager = IndexManager(store, (index,))
    store.attach_index_manager(manager)
    return store, manager, index


def test_index_contract_and_value_objects_are_immutable() -> None:
    index = InMemorySearchIndex()
    assert isinstance(index, SearchIndex)
    assert index.capabilities == IndexCapabilities()
    assert index.statistics() == IndexStatistics()
    with pytest.raises(TypeError):
        SearchIndex()

    result = IndexResult(metadata=(("backend", "memory"),))
    assert result.metadata_value("backend") == "memory"
    assert canonical_json(result).startswith('{"identities":[],"metadata":')
    with pytest.raises(FrozenInstanceError):
        result.identities = ()  # type: ignore[misc]


def test_identity_and_kind_indexes_are_hash_based_and_deterministic() -> None:
    index = InMemorySearchIndex()
    first = entity("A")
    second = entity("B")
    index.add(second)
    index.add(first)

    by_identity = index.lookup(Equals("identity", first.id))
    by_kind = index.lookup(KindIs("entity"))

    assert by_identity is not None
    assert by_identity.identities == (first.id,)
    assert by_kind is not None
    assert by_kind.identities == tuple(sorted((first.id, second.id), key=str))
    assert index.statistics() == IndexStatistics(
        entity_count=2,
        identity_key_count=2,
        kind_key_count=1,
        namespace_key_count=0,
    )



def test_namespace_index_uses_declared_entity_namespace() -> None:
    index = InMemorySearchIndex()
    extension = ExtensionDefinition(
        ExtensionId.new(),
        "org.example.biology",
        "Biology",
        "1.0.0",
    )
    index.add(extension)

    result = index.lookup(NamespaceIs("org.example.biology"))
    assert result is not None
    assert result.identities == (extension.id,)
    assert index.statistics().namespace_key_count == 1

def test_index_supports_safe_boolean_composition_and_falls_back_when_needed() -> None:
    index = InMemorySearchIndex()
    item = entity("A")
    index.add(item)

    conjunction = index.lookup(And((KindIs("entity"), Equals("identity", item.id))))
    disjunction = index.lookup(Or((KindIs("entity"), KindIs("knowledge_unit"))))

    assert conjunction is not None and conjunction.identities == (item.id,)
    assert disjunction is not None and disjunction.identities == (item.id,)
    assert index.lookup(NotEquals("label", "B")) is None


def test_index_manager_rebuilds_only_from_store_and_can_be_discarded() -> None:
    store = InMemoryKnowledgeStore()
    items = (entity("A"), entity("B"))
    store.save_many(items)
    index = InMemorySearchIndex()
    manager = IndexManager(store, (index,))

    statistics = manager.rebuild()
    assert statistics == (
        IndexStatistics(2, 2, 1, 0),
    )
    index.clear()
    assert index.statistics().entity_count == 0
    manager.rebuild()
    assert index.lookup(KindIs("entity")).identities == tuple(
        sorted((item.id for item in items), key=str)
    )


def test_store_updates_attached_indexes_on_save_replace_delete_and_clear() -> None:
    store, _, index = indexed_store()
    original = entity("Original")
    store.save(original)
    assert index.lookup(KindIs("entity")).identities == (original.id,)

    replacement = Entity(original.id, "person", "Replacement")
    from knowledge_architect.kir import StoreConflictPolicy

    store.save(replacement, conflict_policy=StoreConflictPolicy.REPLACE)
    assert index.statistics().entity_count == 1
    store.delete(original.id)
    assert index.lookup(KindIs("entity")).identities == ()

    store.save(entity("Again"))
    store.clear()
    assert index.statistics() == IndexStatistics()


def test_query_results_are_identical_with_and_without_indexes() -> None:
    plain = InMemoryKnowledgeStore()
    indexed, _, _ = indexed_store()
    items = (entity("Gamma"), entity("Alpha"), entity("Beta"))
    plain.save_many(items)
    indexed.save_many(items)

    queries = (
        Query(predicate=KindIs("entity")),
        Query(predicate=Equals("identity", items[1].id)),
        Query(predicate=And((KindIs("entity"), Equals("identity", items[2].id)))),
        Query(predicate=NotEquals("label", "Alpha")),
        Query(predicate=NamespaceIs("biology")),
    )
    for query in queries:
        assert indexed.query(query) == plain.query(query)


def test_invalid_index_never_changes_query_semantics() -> None:
    store, manager, index = indexed_store()
    item = entity("A")
    store.save(item)
    manager.invalidate()

    assert not index.is_valid
    assert manager.candidates(Query(predicate=KindIs("entity"))) is None
    assert store.query(Query(predicate=KindIs("entity"))).elements == (item,)
