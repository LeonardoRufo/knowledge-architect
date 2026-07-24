from __future__ import annotations

from abc import abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256
from typing import Any, TypeAlias

from .entity import Entity
from .identity import EntityId, KIRIdentity
from .query import Query, QueryResult
from .serialization import canonical_json
from .store import (
    InMemoryKnowledgeStore,
    KnowledgeStore,
    StoreConflictPolicy,
)

PrimitiveValue: TypeAlias = str | int | float | bool | None
MetadataEntry: TypeAlias = tuple[str, PrimitiveValue]


class RevisionId(KIRIdentity):
    prefix = "rev"


class SnapshotId(KIRIdentity):
    prefix = "snapshot"


class RevisionStatus(StrEnum):
    ACTIVE = "active"
    DELETED = "deleted"


class VersioningError(Exception):
    """Base exception for versioning and snapshot failures."""


class RevisionNotFoundError(VersioningError):
    """Raised when a requested revision does not exist."""


class RevisionConflictError(VersioningError):
    """Raised when optimistic concurrency detects a stale writer."""


class InvalidRevisionError(VersioningError):
    """Raised when revision invariants are violated."""


class SnapshotNotFoundError(VersioningError):
    """Raised when a requested snapshot does not exist."""


class SnapshotConsistencyError(VersioningError):
    """Raised when a snapshot cannot be created or reconstructed consistently."""


class UnsupportedVersioningCapabilityError(VersioningError):
    """Raised when a backend does not implement a requested capability."""


def _metadata(
    entries: Mapping[str, PrimitiveValue] | tuple[MetadataEntry, ...] | None,
) -> tuple[MetadataEntry, ...]:
    if entries is None:
        return ()
    materialized = tuple(entries.items()) if isinstance(entries, Mapping) else tuple(entries)
    normalized: list[MetadataEntry] = []
    seen: set[str] = set()
    for key, value in materialized:
        key = key.strip()
        if not key:
            raise ValueError("metadata keys must not be empty")
        if key in seen:
            raise ValueError("metadata keys must be unique")
        if value is not None and not isinstance(value, (str, int, float, bool)):
            raise TypeError("metadata values must be primitive")
        seen.add(key)
        normalized.append((key, value))
    return tuple(sorted(normalized, key=lambda item: item[0]))


@dataclass(frozen=True, slots=True)
class RevisionMetadata:
    entries: tuple[MetadataEntry, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "entries", _metadata(self.entries))

    def value(self, key: str, default: PrimitiveValue = None) -> PrimitiveValue:
        return dict(self.entries).get(key, default)


@dataclass(frozen=True, slots=True)
class RevisionReference:
    entity_id: EntityId
    revision_id: RevisionId


@dataclass(frozen=True, slots=True)
class EntityRevision:
    entity_id: EntityId
    revision_id: RevisionId
    revision_number: int
    entity: Entity | None
    previous_revision_id: RevisionId | None
    status: RevisionStatus
    created_at: datetime
    effective_at: datetime | None = None
    metadata: RevisionMetadata = field(default_factory=RevisionMetadata)
    canonical_hash: str | None = None

    def __post_init__(self) -> None:
        if self.revision_number < 1:
            raise InvalidRevisionError("revision_number must be positive")
        if self.created_at.tzinfo is None:
            raise InvalidRevisionError("created_at must be timezone-aware")
        if self.effective_at is not None and self.effective_at.tzinfo is None:
            raise InvalidRevisionError("effective_at must be timezone-aware")
        if self.status is RevisionStatus.ACTIVE:
            if self.entity is None:
                raise InvalidRevisionError("active revision requires an entity payload")
            if self.entity.id != self.entity_id:
                raise InvalidRevisionError("entity payload identity does not match entity_id")
        elif self.entity is not None:
            raise InvalidRevisionError("deleted revision must not contain an entity payload")
        if self.revision_number == 1 and self.previous_revision_id is not None:
            raise InvalidRevisionError("initial revision cannot have a previous revision")
        if self.revision_number > 1 and self.previous_revision_id is None:
            raise InvalidRevisionError("subsequent revision requires a previous revision")


@dataclass(frozen=True, slots=True, order=True)
class SnapshotEntry:
    entity_id: EntityId
    revision_id: RevisionId


@dataclass(frozen=True, slots=True)
class KnowledgeSnapshot:
    snapshot_id: SnapshotId
    created_at: datetime
    revisions: tuple[SnapshotEntry, ...] = field(default_factory=tuple)
    metadata: tuple[MetadataEntry, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.created_at.tzinfo is None:
            raise SnapshotConsistencyError("snapshot created_at must be timezone-aware")
        ordered = tuple(sorted(self.revisions, key=lambda item: str(item.entity_id)))
        if len({entry.entity_id for entry in ordered}) != len(ordered):
            raise SnapshotConsistencyError("snapshot contains duplicate entity identities")
        object.__setattr__(self, "revisions", ordered)
        object.__setattr__(self, "metadata", _metadata(self.metadata))


@dataclass(frozen=True, slots=True)
class VersioningCapabilities:
    revisions: bool = True
    snapshots: bool = True
    optimistic_concurrency: bool = True
    tombstones: bool = True
    historical_queries: bool = False
    revision_references: bool = True


class VersionedKnowledgeStore(KnowledgeStore):
    """Persistence Port extended with immutable revisions and snapshots."""

    @property
    @abstractmethod
    def versioning_capabilities(self) -> VersioningCapabilities: ...

    @abstractmethod
    def save_revision(
        self,
        entity: Entity,
        *,
        expected_revision_id: RevisionId | None = None,
        effective_at: datetime | None = None,
        metadata: Mapping[str, PrimitiveValue] | None = None,
    ) -> EntityRevision: ...

    @abstractmethod
    def load_current(
        self, entity_id: EntityId, *, include_deleted: bool = False
    ) -> EntityRevision: ...

    @abstractmethod
    def load_revision(
        self, entity_id: EntityId, revision_id: RevisionId
    ) -> EntityRevision: ...

    @abstractmethod
    def history(
        self, entity_id: EntityId, *, include_deleted: bool = True
    ) -> tuple[EntityRevision, ...]: ...

    @abstractmethod
    def delete_revision(
        self, entity_id: EntityId, *, expected_revision_id: RevisionId
    ) -> EntityRevision: ...

    @abstractmethod
    def create_snapshot(
        self,
        *,
        include_deleted: bool = False,
        metadata: Mapping[str, PrimitiveValue] | None = None,
    ) -> KnowledgeSnapshot: ...

    @abstractmethod
    def load_snapshot(self, snapshot_id: SnapshotId) -> tuple[EntityRevision, ...]: ...


class InMemoryVersionedKnowledgeStore(InMemoryKnowledgeStore, VersionedKnowledgeStore):
    """Reference in-memory store with linear histories and immutable snapshots."""

    def __init__(self, index_manager: Any | None = None) -> None:
        super().__init__(index_manager=index_manager)
        self._current: dict[EntityId, RevisionId] = {}
        self._revisions: dict[RevisionId, EntityRevision] = {}
        self._history: dict[EntityId, list[RevisionId]] = {}
        self._snapshots: dict[SnapshotId, KnowledgeSnapshot] = {}
        self._versioning_capabilities = VersioningCapabilities()

    @property
    def versioning_capabilities(self) -> VersioningCapabilities:
        return self._versioning_capabilities

    def save_revision(
        self,
        entity: Entity,
        *,
        expected_revision_id: RevisionId | None = None,
        effective_at: datetime | None = None,
        metadata: Mapping[str, PrimitiveValue] | None = None,
    ) -> EntityRevision:
        if not isinstance(entity, Entity):
            raise TypeError("versioned entities must be Entity instances")
        with self._lock:
            current_id = self._current.get(entity.id)
            self._check_expectation(entity.id, current_id, expected_revision_id)
            number = len(self._history.get(entity.id, ())) + 1
            revision_id = RevisionId.new()
            digest = sha256(canonical_json(entity).encode("utf-8")).hexdigest()
            revision = EntityRevision(
                entity_id=entity.id,
                revision_id=revision_id,
                revision_number=number,
                entity=entity,
                previous_revision_id=current_id,
                status=RevisionStatus.ACTIVE,
                created_at=datetime.now(UTC),
                effective_at=effective_at,
                metadata=RevisionMetadata(_metadata(metadata)),
                canonical_hash=digest,
            )
            self._persist_revision(revision)
            return revision

    def load_current(
        self, entity_id: EntityId, *, include_deleted: bool = False
    ) -> EntityRevision:
        if not isinstance(entity_id, EntityId):
            raise TypeError("entity_id must be an EntityId")
        with self._lock:
            revision_id = self._current.get(entity_id)
            if revision_id is None:
                raise RevisionNotFoundError(f"no history for entity: {entity_id}")
            revision = self._revisions[revision_id]
            if revision.status is RevisionStatus.DELETED and not include_deleted:
                raise RevisionNotFoundError(f"entity is deleted: {entity_id}")
            return revision

    def load_revision(
        self, entity_id: EntityId, revision_id: RevisionId
    ) -> EntityRevision:
        with self._lock:
            revision = self._revisions.get(revision_id)
            if revision is None or revision.entity_id != entity_id:
                raise RevisionNotFoundError(
                    f"revision {revision_id} not found for entity {entity_id}"
                )
            return revision

    def history(
        self, entity_id: EntityId, *, include_deleted: bool = True
    ) -> tuple[EntityRevision, ...]:
        with self._lock:
            identifiers = self._history.get(entity_id)
            if identifiers is None:
                raise RevisionNotFoundError(f"no history for entity: {entity_id}")
            revisions = tuple(self._revisions[item] for item in identifiers)
            if include_deleted:
                return revisions
            return tuple(item for item in revisions if item.status is RevisionStatus.ACTIVE)

    def delete_revision(
        self, entity_id: EntityId, *, expected_revision_id: RevisionId
    ) -> EntityRevision:
        with self._lock:
            current_id = self._current.get(entity_id)
            self._check_expectation(entity_id, current_id, expected_revision_id)
            if current_id is None:
                raise RevisionNotFoundError(f"no history for entity: {entity_id}")
            current = self._revisions[current_id]
            if current.status is RevisionStatus.DELETED:
                raise InvalidRevisionError(f"entity is already deleted: {entity_id}")
            revision = EntityRevision(
                entity_id=entity_id,
                revision_id=RevisionId.new(),
                revision_number=current.revision_number + 1,
                entity=None,
                previous_revision_id=current_id,
                status=RevisionStatus.DELETED,
                created_at=datetime.now(UTC),
                metadata=RevisionMetadata((('operation', 'delete'),)),
            )
            self._persist_revision(revision)
            return revision

    def create_snapshot(
        self,
        *,
        include_deleted: bool = False,
        metadata: Mapping[str, PrimitiveValue] | None = None,
    ) -> KnowledgeSnapshot:
        with self._lock:
            entries = tuple(
                SnapshotEntry(entity_id, revision_id)
                for entity_id, revision_id in self._current.items()
                if include_deleted
                or self._revisions[revision_id].status is RevisionStatus.ACTIVE
            )
            snapshot = KnowledgeSnapshot(
                snapshot_id=SnapshotId.new(),
                created_at=datetime.now(UTC),
                revisions=entries,
                metadata=_metadata(metadata),
            )
            for entry in snapshot.revisions:
                if entry.revision_id not in self._revisions:
                    raise SnapshotConsistencyError(
                        f"snapshot references missing revision: {entry.revision_id}"
                    )
            self._snapshots[snapshot.snapshot_id] = snapshot
            return snapshot

    def load_snapshot(self, snapshot_id: SnapshotId) -> tuple[EntityRevision, ...]:
        with self._lock:
            snapshot = self._snapshots.get(snapshot_id)
            if snapshot is None:
                raise SnapshotNotFoundError(f"snapshot not found: {snapshot_id}")
            try:
                return tuple(self._revisions[entry.revision_id] for entry in snapshot.revisions)
            except KeyError as exc:
                raise SnapshotConsistencyError(
                    "snapshot references a missing revision"
                ) from exc

    def query(self, query: Query, *, snapshot_id: SnapshotId | None = None) -> QueryResult:
        if snapshot_id is None:
            return super().query(query)
        revisions = self.load_snapshot(snapshot_id)
        temporary = InMemoryKnowledgeStore()
        temporary.save_many(
            revision.entity
            for revision in revisions
            if revision.status is RevisionStatus.ACTIVE and revision.entity is not None
        )
        result = temporary.query(query)
        return QueryResult(
            elements=result.elements,
            metadata=result.metadata + (("snapshot_id", snapshot_id.value),),
            statistics=result.statistics,
        )

    def clear(self):
        with self._lock:
            result = super().clear()
            self._current.clear()
            self._revisions.clear()
            self._history.clear()
            self._snapshots.clear()
            return result

    def validate_history(self, entity_id: EntityId) -> bool:
        revisions = self.history(entity_id)
        previous: RevisionId | None = None
        for number, revision in enumerate(revisions, start=1):
            if revision.revision_number != number:
                raise InvalidRevisionError("revision numbers are not monotonic")
            if revision.previous_revision_id != previous:
                raise InvalidRevisionError("revision chain is not linear")
            previous = revision.revision_id
        if self._current[entity_id] != previous:
            raise InvalidRevisionError("current pointer does not reference history tail")
        return True

    def _check_expectation(
        self,
        entity_id: EntityId,
        current_id: RevisionId | None,
        expected_id: RevisionId | None,
    ) -> None:
        if current_id is None:
            if expected_id is not None:
                raise RevisionConflictError(
                    f"entity {entity_id} has no current revision; expected {expected_id}"
                )
            return
        if expected_id is None:
            raise RevisionConflictError(
                f"entity {entity_id} already has history; expected revision is required"
            )
        if expected_id != current_id:
            raise RevisionConflictError(
                f"stale revision for {entity_id}: expected {expected_id}, current {current_id}"
            )

    def _persist_revision(self, revision: EntityRevision) -> None:
        if revision.revision_id in self._revisions:
            raise InvalidRevisionError(f"duplicate revision id: {revision.revision_id}")
        entity_id = revision.entity_id
        old_entities = dict(self._entities)
        old_canonical = dict(self._canonical)
        old_current = dict(self._current)
        old_revisions = dict(self._revisions)
        old_history = {key: list(value) for key, value in self._history.items()}
        try:
            self._revisions[revision.revision_id] = revision
            self._history.setdefault(entity_id, []).append(revision.revision_id)
            self._current[entity_id] = revision.revision_id
            if revision.status is RevisionStatus.ACTIVE:
                assert revision.entity is not None
                super().save(revision.entity, conflict_policy=StoreConflictPolicy.REPLACE)
            elif super().exists(entity_id):
                super().delete(entity_id)
            self.validate_history(entity_id)
        except Exception:
            self._entities = old_entities
            self._canonical = old_canonical
            self._current = old_current
            self._revisions = old_revisions
            self._history = old_history
            if self._index_manager is not None:
                self._index_manager.rebuild()
            raise
