from dataclasses import FrozenInstanceError, replace

import pytest

from knowledge_architect.kir import (
    Entity,
    EntityId,
    IndexManager,
    InMemorySearchIndex,
    InMemoryVersionedKnowledgeStore,
    KindIs,
    Query,
    RevisionConflictError,
    RevisionNotFoundError,
    RevisionStatus,
    SnapshotId,
    SnapshotNotFoundError,
    VersionedKnowledgeStore,
    canonical_json,
)


def entity(label: str = "Original") -> Entity:
    return Entity(EntityId.new(), "concept", label)


def test_initial_and_subsequent_revisions_preserve_linear_history() -> None:
    store = InMemoryVersionedKnowledgeStore()
    first_entity = entity()
    first = store.save_revision(first_entity)
    second_entity = replace(first_entity, label="Updated")
    second = store.save_revision(second_entity, expected_revision_id=first.revision_id)

    assert first.revision_number == 1
    assert first.previous_revision_id is None
    assert second.revision_number == 2
    assert second.previous_revision_id == first.revision_id
    assert store.load_current(first_entity.id) == second
    assert store.load_revision(first_entity.id, first.revision_id) == first
    assert store.history(first_entity.id) == (first, second)
    assert store.validate_history(first_entity.id)


def test_revision_is_immutable_and_serialization_is_canonical() -> None:
    revision = InMemoryVersionedKnowledgeStore().save_revision(entity())
    assert canonical_json(revision) == canonical_json(revision)
    assert revision.canonical_hash is not None
    with pytest.raises(FrozenInstanceError):
        revision.revision_number = 2  # type: ignore[misc]


def test_optimistic_concurrency_rejects_stale_or_implicit_update() -> None:
    store = InMemoryVersionedKnowledgeStore()
    item = entity()
    first = store.save_revision(item)
    second = store.save_revision(replace(item, label="R2"), expected_revision_id=first.revision_id)
    with pytest.raises(RevisionConflictError):
        store.save_revision(replace(item, label="stale"), expected_revision_id=first.revision_id)
    with pytest.raises(RevisionConflictError):
        store.save_revision(replace(item, label="implicit"))
    assert store.load_current(item.id) == second


def test_tombstone_hides_current_preserves_history_and_supports_restore() -> None:
    store = InMemoryVersionedKnowledgeStore()
    item = entity()
    active = store.save_revision(item)
    deleted = store.delete_revision(item.id, expected_revision_id=active.revision_id)

    assert deleted.status is RevisionStatus.DELETED
    assert deleted.entity is None
    assert not store.exists(item.id)
    with pytest.raises(RevisionNotFoundError):
        store.load_current(item.id)
    assert store.load_current(item.id, include_deleted=True) == deleted
    assert store.history(item.id) == (active, deleted)

    restored = store.save_revision(item, expected_revision_id=deleted.revision_id)
    assert restored.status is RevisionStatus.ACTIVE
    assert restored.revision_number == 3
    assert store.load(item.id) == item


def test_empty_and_multi_entity_snapshots_are_deterministic() -> None:
    store = InMemoryVersionedKnowledgeStore()
    assert store.load_snapshot(store.create_snapshot().snapshot_id) == ()
    items = (entity("B"), entity("A"))
    revisions = tuple(store.save_revision(item) for item in items)
    snapshot = store.create_snapshot(metadata={"purpose": "test"})

    assert tuple(entry.entity_id for entry in snapshot.revisions) == tuple(
        sorted((item.id for item in items), key=str)
    )
    assert {revision.revision_id for revision in store.load_snapshot(snapshot.snapshot_id)} == {
        revision.revision_id for revision in revisions
    }
    with pytest.raises(FrozenInstanceError):
        snapshot.revisions = ()  # type: ignore[misc]


def test_snapshot_reconstructs_old_state_after_update_and_delete() -> None:
    store = InMemoryVersionedKnowledgeStore()
    item = entity("R1")
    first = store.save_revision(item)
    before = store.create_snapshot()
    second = store.save_revision(replace(item, label="R2"), expected_revision_id=first.revision_id)
    store.delete_revision(item.id, expected_revision_id=second.revision_id)

    historical = store.load_snapshot(before.snapshot_id)
    assert historical == (first,)
    assert historical[0].entity.label == "R1"
    result = store.query(
        Query(predicate=KindIs("entity")), snapshot_id=before.snapshot_id
    )
    assert result.elements == (item,)


def test_snapshot_can_include_tombstones_and_unknown_snapshot_fails() -> None:
    store = InMemoryVersionedKnowledgeStore()
    item = entity()
    first = store.save_revision(item)
    tombstone = store.delete_revision(item.id, expected_revision_id=first.revision_id)
    assert store.create_snapshot().revisions == ()
    snapshot = store.create_snapshot(include_deleted=True)
    assert store.load_snapshot(snapshot.snapshot_id) == (tombstone,)
    with pytest.raises(SnapshotNotFoundError):
        store.load_snapshot(SnapshotId.new())


def test_current_index_tracks_only_active_revision() -> None:
    store = InMemoryVersionedKnowledgeStore()
    index = InMemorySearchIndex()
    manager = IndexManager(store, (index,))
    store.attach_index_manager(manager)
    item = entity()
    first = store.save_revision(item)
    assert index.lookup(KindIs("entity")).identities == (item.id,)
    deleted = store.delete_revision(item.id, expected_revision_id=first.revision_id)
    assert index.lookup(KindIs("entity")).identities == ()
    store.save_revision(item, expected_revision_id=deleted.revision_id)
    assert index.lookup(KindIs("entity")).identities == (item.id,)


def test_versioned_store_remains_compatible_with_knowledge_store() -> None:
    store = InMemoryVersionedKnowledgeStore()
    assert isinstance(store, VersionedKnowledgeStore)
    item = entity()
    store.save_revision(item)
    assert store.load(item.id) is item
    assert store.count() == 1
