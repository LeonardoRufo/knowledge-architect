from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, TypeAlias

from .identity import KIRIdentity
from .query import And, Equals, KindIs, NamespaceIs, Or, Predicate, Query

if TYPE_CHECKING:
    from .store import KnowledgeStore, StoreEntity

IndexEntry: TypeAlias = tuple[str, str | int | float | bool | None]


def _normalize_entries(
    entries: tuple[IndexEntry, ...], field_name: str
) -> tuple[IndexEntry, ...]:
    keys: set[str] = set()
    normalized: list[IndexEntry] = []
    for key, value in entries:
        normalized_key = key.strip()
        if not normalized_key:
            raise ValueError(f"{field_name} keys must not be empty")
        if normalized_key in keys:
            raise ValueError(f"{field_name} keys must be unique")
        keys.add(normalized_key)
        normalized.append((normalized_key, value))
    return tuple(sorted(normalized, key=lambda item: item[0]))


def _kind_name(entity: Any) -> str:
    name = type(entity).__name__
    return "".join(
        f"_{character.lower()}" if character.isupper() else character
        for character in name
    ).lstrip("_")


def _namespace(entity: Any) -> str | None:
    namespace = getattr(entity, "namespace", None)
    if isinstance(namespace, str):
        return namespace
    identity = getattr(entity, "id", None)
    identity_namespace = getattr(identity, "namespace", None)
    return identity_namespace if isinstance(identity_namespace, str) else None


@dataclass(frozen=True, slots=True)
class IndexCapabilities:
    equality_lookup: bool = True
    ordering: bool = False
    prefix_search: bool = False
    range_search: bool = False
    identity: bool = True
    kind: bool = True
    namespace: bool = True


@dataclass(frozen=True, slots=True)
class IndexStatistics:
    entity_count: int = 0
    identity_key_count: int = 0
    kind_key_count: int = 0
    namespace_key_count: int = 0

    def __post_init__(self) -> None:
        values = (
            self.entity_count,
            self.identity_key_count,
            self.kind_key_count,
            self.namespace_key_count,
        )
        if any(value < 0 for value in values):
            raise ValueError("index statistics must not be negative")


@dataclass(frozen=True, slots=True)
class IndexResult:
    identities: tuple[KIRIdentity, ...] = field(default_factory=tuple)
    metadata: tuple[IndexEntry, ...] = field(default_factory=tuple)
    statistics: IndexStatistics = field(default_factory=IndexStatistics)

    def __post_init__(self) -> None:
        if len(set(self.identities)) != len(self.identities):
            raise ValueError("index result identities must be unique")
        object.__setattr__(self, "identities", tuple(sorted(self.identities, key=str)))
        object.__setattr__(self, "metadata", _normalize_entries(self.metadata, "metadata"))

    def metadata_value(
        self, key: str, default: str | float | bool | None = None
    ) -> str | int | float | bool | None:
        return dict(self.metadata).get(key, default)


class SearchIndex(ABC):
    """Storage-independent contract for disposable, derived index data."""

    @property
    @abstractmethod
    def capabilities(self) -> IndexCapabilities:
        """Describe the lookup capabilities supported by this index."""

    @property
    @abstractmethod
    def is_valid(self) -> bool:
        """Return whether the index can currently be used."""

    @abstractmethod
    def add(self, entity: StoreEntity) -> None:
        """Add or replace the derived entries for one entity."""

    @abstractmethod
    def remove(self, identity: KIRIdentity) -> None:
        """Remove derived entries for an identity, if present."""

    @abstractmethod
    def clear(self) -> None:
        """Discard all derived entries."""

    @abstractmethod
    def invalidate(self) -> None:
        """Mark the index unusable until it is rebuilt."""

    @abstractmethod
    def rebuild(self, entities: tuple[StoreEntity, ...]) -> IndexStatistics:
        """Reconstruct the index exclusively from Store entities."""

    @abstractmethod
    def lookup(self, predicate: Predicate) -> IndexResult | None:
        """Return candidates, or None when the predicate is not safely indexable."""

    @abstractmethod
    def statistics(self) -> IndexStatistics:
        """Return deterministic statistics for the current derived data."""


class InMemorySearchIndex(SearchIndex):
    """Reference hash-based identity, kind, and namespace index."""

    def __init__(self) -> None:
        self._entities: dict[KIRIdentity, tuple[str, str | None]] = {}
        self._kinds: dict[str, set[KIRIdentity]] = {}
        self._namespaces: dict[str, set[KIRIdentity]] = {}
        self._valid = True
        self._capabilities = IndexCapabilities()

    @property
    def capabilities(self) -> IndexCapabilities:
        return self._capabilities

    @property
    def is_valid(self) -> bool:
        return self._valid

    def add(self, entity: StoreEntity) -> None:
        identity = getattr(entity, "id", None)
        if not isinstance(identity, KIRIdentity):
            raise TypeError("indexed entities must expose a typed KIR identity in 'id'")
        self.remove(identity)
        kind = _kind_name(entity)
        namespace = _namespace(entity)
        self._entities[identity] = (kind, namespace)
        self._kinds.setdefault(kind, set()).add(identity)
        if namespace is not None:
            self._namespaces.setdefault(namespace, set()).add(identity)

    def remove(self, identity: KIRIdentity) -> None:
        previous = self._entities.pop(identity, None)
        if previous is None:
            return
        kind, namespace = previous
        self._discard(self._kinds, kind, identity)
        if namespace is not None:
            self._discard(self._namespaces, namespace, identity)

    def clear(self) -> None:
        self._entities.clear()
        self._kinds.clear()
        self._namespaces.clear()
        self._valid = True

    def invalidate(self) -> None:
        self._valid = False

    def rebuild(self, entities: tuple[StoreEntity, ...]) -> IndexStatistics:
        self.clear()
        try:
            for entity in entities:
                self.add(entity)
        except Exception:
            self.invalidate()
            raise
        self._valid = True
        return self.statistics()

    def lookup(self, predicate: Predicate) -> IndexResult | None:
        if not self._valid:
            return None
        identities = self._lookup_identities(predicate)
        if identities is None:
            return None
        return IndexResult(
            identities=tuple(identities),
            metadata=(
                ("backend", "memory"),
                ("indexable", True),
            ),
            statistics=self.statistics(),
        )

    def statistics(self) -> IndexStatistics:
        return IndexStatistics(
            entity_count=len(self._entities),
            identity_key_count=len(self._entities),
            kind_key_count=len(self._kinds),
            namespace_key_count=len(self._namespaces),
        )

    def _lookup_identities(self, predicate: Predicate) -> set[KIRIdentity] | None:
        if isinstance(predicate, Equals) and predicate.field == "identity":
            identity = predicate.value
            if isinstance(identity, KIRIdentity):
                return {identity} if identity in self._entities else set()
            return {
                candidate
                for candidate in self._entities
                if candidate.value == identity or str(candidate) == identity
            }
        if isinstance(predicate, KindIs):
            return set(self._kinds.get(predicate.kind, set()))
        if isinstance(predicate, NamespaceIs):
            return set(self._namespaces.get(predicate.namespace, set()))
        if isinstance(predicate, And):
            parts = [self._lookup_identities(item) for item in predicate.predicates]
            if any(part is None for part in parts):
                return None
            concrete = [part for part in parts if part is not None]
            if not concrete:
                return set()
            result = set(concrete[0])
            for part in concrete[1:]:
                result.intersection_update(part)
            return result
        if isinstance(predicate, Or):
            parts = [self._lookup_identities(item) for item in predicate.predicates]
            if any(part is None for part in parts):
                return None
            result: set[KIRIdentity] = set()
            for part in parts:
                if part is not None:
                    result.update(part)
            return result
        return None

    @staticmethod
    def _discard(
        mapping: dict[str, set[KIRIdentity]], key: str, identity: KIRIdentity
    ) -> None:
        values = mapping.get(key)
        if values is None:
            return
        values.discard(identity)
        if not values:
            del mapping[key]


class IndexManager:
    """Coordinates derived indexes while preserving KnowledgeStore authority."""

    def __init__(
        self,
        store: KnowledgeStore,
        indexes: tuple[SearchIndex, ...] | None = None,
    ) -> None:
        self._store = store
        self._indexes = indexes or (InMemorySearchIndex(),)

    @property
    def indexes(self) -> tuple[SearchIndex, ...]:
        return self._indexes

    def rebuild(self) -> tuple[IndexStatistics, ...]:
        entities = self._store.list()
        return tuple(index.rebuild(entities) for index in self._indexes)

    def invalidate(self) -> None:
        for index in self._indexes:
            index.invalidate()

    def clear(self) -> None:
        for index in self._indexes:
            index.clear()

    def entity_saved(self, entity: StoreEntity) -> None:
        self._update(lambda index: index.add(entity))

    def entity_deleted(self, identity: KIRIdentity) -> None:
        self._update(lambda index: index.remove(identity))

    def candidates(self, query: Query) -> tuple[KIRIdentity, ...] | None:
        if query.predicate is None or query.traversal is not None or query.origin:
            return None
        for index in self._indexes:
            result = index.lookup(query.predicate)
            if result is not None:
                return result.identities
        return None

    def _update(self, operation: Any) -> None:
        for index in self._indexes:
            if not index.is_valid:
                continue
            try:
                operation(index)
            except Exception:
                index.invalidate()
                raise