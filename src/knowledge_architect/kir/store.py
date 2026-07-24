from __future__ import annotations

from abc import ABC, abstractmethod
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import StrEnum
from threading import RLock
from typing import Any, Self, TypeAlias

from .identity import KIRIdentity
from .query import (
    Ancestors,
    And,
    Children,
    Descendants,
    Equals,
    HasEvidence,
    HasRelation,
    HasTransformation,
    KindIs,
    NamespaceIs,
    Neighbors,
    Not,
    NotEquals,
    Or,
    Parents,
    Predicate,
    Query,
    QueryResult,
    ShortestPath,
)
from .relation import Relation
from .serialization import canonical_json, to_primitive
from .transformation import KnowledgeUnitTransformation

StoreEntity: TypeAlias = Any
StoreEntry: TypeAlias = tuple[str, str | int | float | bool | None]


class StoreError(Exception):
    """Base exception for KnowledgeStore failures."""


class DuplicateIdentityError(StoreError):
    """Raised when a save conflicts with an existing identity."""


class EntityNotFoundError(StoreError):
    """Raised when an identity is not present in the store."""


class SerializationError(StoreError):
    """Raised when an entity cannot be canonically serialized."""


class TransactionError(StoreError):
    """Raised when a transaction cannot be completed."""


class StoreConflictPolicy(StrEnum):
    REJECT = "reject"
    REPLACE = "replace"
    UPDATE = "update"


@dataclass(frozen=True, slots=True)
class StoreCapabilities:
    transactions: bool = False
    queries: bool = True
    traversals: bool = False
    conflict_policies: tuple[StoreConflictPolicy, ...] = (
        StoreConflictPolicy.REJECT,
        StoreConflictPolicy.REPLACE,
        StoreConflictPolicy.UPDATE,
    )


@dataclass(frozen=True, slots=True)
class StoreResult:
    entity: StoreEntity | None = None
    metadata: tuple[StoreEntry, ...] = field(default_factory=tuple)
    statistics: tuple[StoreEntry, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", _normalize_entries(self.metadata, "metadata"))
        object.__setattr__(
            self, "statistics", _normalize_entries(self.statistics, "statistics")
        )

    def metadata_value(
        self, key: str, default: str | float | bool | None = None
    ) -> str | int | float | bool | None:
        return dict(self.metadata).get(key, default)

    def statistic(
        self, key: str, default: str | float | bool | None = None
    ) -> str | int | float | bool | None:
        return dict(self.statistics).get(key, default)


class StoreTransaction(ABC):
    """Logical persistence unit exposed independently from transaction technology."""

    @abstractmethod
    def save(
        self,
        entity: StoreEntity,
        *,
        conflict_policy: StoreConflictPolicy = StoreConflictPolicy.REJECT,
    ) -> StoreResult:
        """Stage or immediately persist an entity."""

    @abstractmethod
    def delete(self, identity: KIRIdentity) -> StoreResult:
        """Stage or immediately delete an entity."""

    @abstractmethod
    def commit(self) -> tuple[StoreResult, ...]:
        """Commit all operations in this logical unit."""

    @abstractmethod
    def rollback(self) -> None:
        """Discard all operations in this logical unit."""

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> bool:
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        return False


class KnowledgeStore(ABC):
    """Backend-independent Port for persistence of immutable KIR objects."""

    @property
    @abstractmethod
    def capabilities(self) -> StoreCapabilities:
        """Return explicitly supported store capabilities."""

    @abstractmethod
    def save(
        self,
        entity: StoreEntity,
        *,
        conflict_policy: StoreConflictPolicy = StoreConflictPolicy.REJECT,
    ) -> StoreResult:
        """Persist one entity without modifying it."""

    def save_many(
        self,
        entities: Iterable[StoreEntity],
        *,
        conflict_policy: StoreConflictPolicy = StoreConflictPolicy.REJECT,
    ) -> tuple[StoreResult, ...]:
        return tuple(
            self.save(entity, conflict_policy=conflict_policy) for entity in entities
        )

    @abstractmethod
    def load(self, identity: KIRIdentity) -> StoreEntity:
        """Load one entity by its canonical typed identity."""

    @abstractmethod
    def exists(self, identity: KIRIdentity) -> bool:
        """Return whether an identity exists."""

    @abstractmethod
    def delete(self, identity: KIRIdentity) -> StoreResult:
        """Delete one entity by identity."""

    @abstractmethod
    def list(self) -> tuple[StoreEntity, ...]:
        """List all entities in deterministic identity order."""

    @abstractmethod
    def count(self) -> int:
        """Return the number of persisted entities."""

    @abstractmethod
    def query(self, query: Query) -> QueryResult:
        """Execute a storage-independent Query."""

    @abstractmethod
    def clear(self) -> StoreResult:
        """Remove all entities."""

    @abstractmethod
    def transaction(self) -> StoreTransaction:
        """Create a logical persistence transaction."""


class InMemoryKnowledgeStore(KnowledgeStore):
    """Reference adapter retaining immutable KIR objects in process memory."""

    def __init__(self) -> None:
        self._entities: dict[KIRIdentity, StoreEntity] = {}
        self._canonical: dict[KIRIdentity, str] = {}
        self._lock = RLock()
        self._capabilities = StoreCapabilities(transactions=True, traversals=True)

    @property
    def capabilities(self) -> StoreCapabilities:
        return self._capabilities

    def save(
        self,
        entity: StoreEntity,
        *,
        conflict_policy: StoreConflictPolicy = StoreConflictPolicy.REJECT,
    ) -> StoreResult:
        identity, serialized = _validate_entity(entity)
        with self._lock:
            exists = identity in self._entities
            if exists and conflict_policy is StoreConflictPolicy.REJECT:
                raise DuplicateIdentityError(f"identity already exists: {identity}")
            self._entities[identity] = entity
            self._canonical[identity] = serialized
        return StoreResult(
            entity=entity,
            metadata=(("conflict_policy", conflict_policy.value), ("operation", "save")),
            statistics=(("created", int(not exists)), ("replaced", int(exists))),
        )

    def save_many(
        self,
        entities: Iterable[StoreEntity],
        *,
        conflict_policy: StoreConflictPolicy = StoreConflictPolicy.REJECT,
    ) -> tuple[StoreResult, ...]:
        materialized = tuple(entities)
        validated = tuple(_validate_entity(entity) for entity in materialized)
        identities = tuple(identity for identity, _ in validated)
        if len(set(identities)) != len(identities):
            raise DuplicateIdentityError("save_many contains duplicate identities")
        with self._lock:
            if conflict_policy is StoreConflictPolicy.REJECT:
                conflicts = sorted(
                    str(identity) for identity in identities if identity in self._entities
                )
                if conflicts:
                    raise DuplicateIdentityError(
                        f"identities already exist: {', '.join(conflicts)}"
                    )
            results: list[StoreResult] = []
            for entity, (identity, serialized) in zip(materialized, validated, strict=True):
                existed = identity in self._entities
                self._entities[identity] = entity
                self._canonical[identity] = serialized
                results.append(
                    StoreResult(
                        entity=entity,
                        metadata=(
                            ("conflict_policy", conflict_policy.value),
                            ("operation", "save"),
                        ),
                        statistics=(("created", int(not existed)), ("replaced", int(existed))),
                    )
                )
        return tuple(results)

    def load(self, identity: KIRIdentity) -> StoreEntity:
        _validate_identity(identity)
        with self._lock:
            try:
                return self._entities[identity]
            except KeyError as exc:
                raise EntityNotFoundError(f"identity not found: {identity}") from exc

    def exists(self, identity: KIRIdentity) -> bool:
        _validate_identity(identity)
        with self._lock:
            return identity in self._entities

    def delete(self, identity: KIRIdentity) -> StoreResult:
        _validate_identity(identity)
        with self._lock:
            try:
                entity = self._entities.pop(identity)
                self._canonical.pop(identity)
            except KeyError as exc:
                raise EntityNotFoundError(f"identity not found: {identity}") from exc
        return StoreResult(
            entity=entity,
            metadata=(("operation", "delete"),),
            statistics=(("deleted", 1),),
        )

    def list(self) -> tuple[StoreEntity, ...]:
        with self._lock:
            return tuple(self._entities[key] for key in sorted(self._entities, key=str))

    def count(self) -> int:
        with self._lock:
            return len(self._entities)

    def query(self, query: Query) -> QueryResult:
        if not isinstance(query, Query):
            raise TypeError("query must be a Query")
        with self._lock:
            entities = dict(self._entities)
        selected = _select_query_candidates(query, entities)
        filtered = tuple(
            entity
            for entity in selected
            if query.predicate is None
            or _matches(query.predicate, entity, tuple(entities.values()))
        )
        ordered = _order_entities(filtered, query)
        offset = query.pagination.offset
        limit = query.pagination.limit
        paginated = ordered[offset:] if limit is None else ordered[offset : offset + limit]
        elements = tuple(_project(entity, query.projection.fields) for entity in paginated)
        return QueryResult(
            elements=elements,
            metadata=(("backend", "memory"),),
            statistics=(("matched", len(filtered)), ("returned", len(elements))),
        )

    def clear(self) -> StoreResult:
        with self._lock:
            removed = len(self._entities)
            self._entities.clear()
            self._canonical.clear()
        return StoreResult(
            metadata=(("operation", "clear"),),
            statistics=(("deleted", removed),),
        )

    def transaction(self) -> StoreTransaction:
        return _InMemoryTransaction(self)


class _InMemoryTransaction(StoreTransaction):
    def __init__(self, store: InMemoryKnowledgeStore) -> None:
        self._store = store
        self._operations: list[tuple[str, Any, StoreConflictPolicy | None]] = []
        self._closed = False

    def save(
        self,
        entity: StoreEntity,
        *,
        conflict_policy: StoreConflictPolicy = StoreConflictPolicy.REJECT,
    ) -> StoreResult:
        self._ensure_open()
        _validate_entity(entity)
        self._operations.append(("save", entity, conflict_policy))
        return StoreResult(entity=entity, metadata=(("operation", "stage_save"),))

    def delete(self, identity: KIRIdentity) -> StoreResult:
        self._ensure_open()
        _validate_identity(identity)
        self._operations.append(("delete", identity, None))
        return StoreResult(metadata=(("operation", "stage_delete"),))

    def commit(self) -> tuple[StoreResult, ...]:
        self._ensure_open()
        with self._store._lock:
            entities_snapshot = dict(self._store._entities)
            canonical_snapshot = dict(self._store._canonical)
            results: list[StoreResult] = []
            try:
                for operation, value, policy in self._operations:
                    if operation == "save":
                        assert policy is not None
                        results.append(self._store.save(value, conflict_policy=policy))
                    else:
                        results.append(self._store.delete(value))
            except Exception as exc:
                self._store._entities = entities_snapshot
                self._store._canonical = canonical_snapshot
                self._closed = True
                raise TransactionError("transaction commit failed and was rolled back") from exc
        self._closed = True
        return tuple(results)

    def rollback(self) -> None:
        self._ensure_open()
        self._operations.clear()
        self._closed = True

    def _ensure_open(self) -> None:
        if self._closed:
            raise TransactionError("transaction is already closed")


def _normalize_entries(entries: tuple[StoreEntry, ...], field_name: str) -> tuple[StoreEntry, ...]:
    keys: set[str] = set()
    normalized: list[StoreEntry] = []
    for key, value in entries:
        key = key.strip()
        if not key:
            raise ValueError(f"{field_name} keys must not be empty")
        if key in keys:
            raise ValueError(f"{field_name} keys must be unique")
        keys.add(key)
        normalized.append((key, value))
    return tuple(sorted(normalized, key=lambda item: item[0]))


def _validate_identity(identity: KIRIdentity) -> None:
    if not isinstance(identity, KIRIdentity):
        raise TypeError("identity must be a KIRIdentity")


def _validate_entity(entity: StoreEntity) -> tuple[KIRIdentity, str]:
    identity = getattr(entity, "id", None)
    if not isinstance(identity, KIRIdentity):
        raise TypeError("persisted entities must expose a typed KIR identity in 'id'")
    try:
        serialized = canonical_json(entity)
    except (TypeError, ValueError) as exc:
        raise SerializationError(f"entity {identity} is not canonically serializable") from exc
    return identity, serialized


def _kind_name(entity: StoreEntity) -> str:
    name = type(entity).__name__
    return "".join(f"_{char.lower()}" if char.isupper() else char for char in name).lstrip("_")


def _field_value(entity: StoreEntity, field_name: str) -> Any:
    if field_name == "identity":
        return getattr(entity, "id", None)
    if field_name == "type":
        return _kind_name(entity)
    current = entity
    for component in field_name.split("."):
        if not hasattr(current, component):
            return None
        current = getattr(current, component)
    return current


def _matches(
    predicate: Predicate,
    entity: StoreEntity,
    all_entities: tuple[StoreEntity, ...],
) -> bool:
    if isinstance(predicate, Equals):
        return _field_value(entity, predicate.field) == predicate.value
    if isinstance(predicate, NotEquals):
        return _field_value(entity, predicate.field) != predicate.value
    if isinstance(predicate, KindIs):
        return _kind_name(entity) == predicate.kind
    if isinstance(predicate, NamespaceIs):
        return _field_value(entity, "namespace") == predicate.namespace
    if isinstance(predicate, HasEvidence):
        evidence_ids = getattr(entity, "evidence_ids", ())
        if not evidence_ids:
            return False
        if predicate.evidence_kind is None:
            return True
        evidence_by_id = {
            item.id: item for item in all_entities if _kind_name(item) == "evidence"
        }
        return any(
            getattr(evidence_by_id.get(identity), "kind", None) == predicate.evidence_kind
            for identity in evidence_ids
        )
    if isinstance(predicate, HasRelation):
        identity = getattr(entity, "id", None)
        return any(
            isinstance(item, Relation)
            and item.relation_type == predicate.relation_kind
            and (item.source.id == identity or item.target.id == identity)
            for item in all_entities
        )
    if isinstance(predicate, HasTransformation):
        identity = getattr(entity, "id", None)
        return any(
            isinstance(item, KnowledgeUnitTransformation)
            and (
                predicate.transformation_kind is None
                or item.kind == predicate.transformation_kind
            )
            and (identity in item.source_ids or identity in item.target_ids)
            for item in all_entities
        )
    if isinstance(predicate, And):
        return all(_matches(item, entity, all_entities) for item in predicate.predicates)
    if isinstance(predicate, Or):
        return any(_matches(item, entity, all_entities) for item in predicate.predicates)
    if isinstance(predicate, Not):
        return not _matches(predicate.predicate, entity, all_entities)
    raise TypeError(f"unsupported predicate: {type(predicate).__name__}")


def _select_query_candidates(
    query: Query, entities: dict[KIRIdentity, StoreEntity]
) -> tuple[StoreEntity, ...]:
    if query.traversal is None:
        if query.origin:
            return tuple(entities[identity] for identity in query.origin if identity in entities)
        return tuple(entities.values())

    relations = tuple(item for item in entities.values() if isinstance(item, Relation))
    adjacency_out: dict[KIRIdentity, list[KIRIdentity]] = {}
    adjacency_in: dict[KIRIdentity, list[KIRIdentity]] = {}
    for relation in relations:
        if (
            isinstance(query.traversal, Neighbors)
            and query.traversal.relation_kind is not None
            and relation.relation_type != query.traversal.relation_kind
        ):
            continue
        adjacency_out.setdefault(relation.source.id, []).append(relation.target.id)
        adjacency_in.setdefault(relation.target.id, []).append(relation.source.id)

    traversal = query.traversal
    if isinstance(traversal, Parents):
        identities = {item for origin in query.origin for item in adjacency_in.get(origin, ())}
    elif isinstance(traversal, Children):
        identities = {item for origin in query.origin for item in adjacency_out.get(origin, ())}
    elif isinstance(traversal, Neighbors):
        identities = {
            item
            for origin in query.origin
            for item in (*adjacency_in.get(origin, ()), *adjacency_out.get(origin, ()))
        }
    elif isinstance(traversal, Ancestors):
        identities = _walk(query.origin, adjacency_in, traversal.max_depth)
    elif isinstance(traversal, Descendants):
        identities = _walk(query.origin, adjacency_out, traversal.max_depth)
    elif isinstance(traversal, ShortestPath):
        undirected: dict[KIRIdentity, list[KIRIdentity]] = {}
        for source, targets in adjacency_out.items():
            for target in targets:
                undirected.setdefault(source, []).append(target)
                undirected.setdefault(target, []).append(source)
        identities = set(_shortest_path(query.origin[0], traversal.target, undirected))
    else:
        raise TypeError(f"unsupported traversal: {type(traversal).__name__}")
    return tuple(
        entities[identity]
        for identity in sorted(identities, key=str)
        if identity in entities
    )


def _walk(
    origins: tuple[KIRIdentity, ...],
    adjacency: dict[KIRIdentity, list[KIRIdentity]],
    max_depth: int | None,
) -> set[KIRIdentity]:
    visited = set(origins)
    result: set[KIRIdentity] = set()
    queue = deque((origin, 0) for origin in origins)
    while queue:
        current, depth = queue.popleft()
        if max_depth is not None and depth >= max_depth:
            continue
        for neighbor in sorted(adjacency.get(current, ()), key=str):
            if neighbor in visited:
                continue
            visited.add(neighbor)
            result.add(neighbor)
            queue.append((neighbor, depth + 1))
    return result


def _shortest_path(
    source: KIRIdentity,
    target: KIRIdentity,
    adjacency: dict[KIRIdentity, list[KIRIdentity]],
) -> tuple[KIRIdentity, ...]:
    queue = deque(((source, (source,)),))
    visited = {source}
    while queue:
        current, path = queue.popleft()
        if current == target:
            return path
        for neighbor in sorted(adjacency.get(current, ()), key=str):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, (*path, neighbor)))
    return ()


def _order_entities(entities: tuple[StoreEntity, ...], query: Query) -> tuple[StoreEntity, ...]:
    result = list(entities)
    if not query.ordering:
        return tuple(sorted(result, key=lambda entity: str(entity.id)))
    for ordering in reversed(query.ordering):
        result.sort(
            key=lambda entity: _sortable(_field_value(entity, ordering.field)),
            reverse=ordering.direction.value == "descending",
        )
    return tuple(result)


def _sortable(value: Any) -> tuple[str, str]:
    if isinstance(value, KIRIdentity):
        return ("identity", value.value)
    return (type(value).__name__, canonical_json(value) if value is not None else "")


def _project(entity: StoreEntity, fields: tuple[str, ...]) -> StoreEntity:
    if not fields:
        return entity
    return tuple((field, to_primitive(_field_value(entity, field))) for field in fields)
