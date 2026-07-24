from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, replace
from enum import StrEnum
from typing import Any, TypeAlias

from .identity import KIRIdentity

QueryScalar: TypeAlias = str | int | float | bool | None
QueryValue: TypeAlias = QueryScalar | KIRIdentity | tuple["QueryValue", ...]
ResultEntry: TypeAlias = tuple[str, QueryValue]


def _validate_non_empty(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized


def _validate_query_value(value: QueryValue, field_name: str = "value") -> None:
    if isinstance(value, (str, int, float, bool, KIRIdentity)) or value is None:
        return
    if isinstance(value, tuple):
        for item in value:
            _validate_query_value(item, field_name)
        return
    raise TypeError(f"{field_name} must be serializable by the KIR canonical serializer")


def _normalize_entries(entries: tuple[ResultEntry, ...], field_name: str) -> tuple[ResultEntry, ...]:
    normalized: list[ResultEntry] = []
    keys: set[str] = set()
    for key, value in entries:
        normalized_key = _validate_non_empty(key, f"{field_name} key")
        if normalized_key in keys:
            raise ValueError(f"{field_name} keys must be unique")
        _validate_query_value(value, f"{field_name}[{normalized_key!r}]")
        keys.add(normalized_key)
        normalized.append((normalized_key, value))
    return tuple(sorted(normalized, key=lambda entry: entry[0]))


@dataclass(frozen=True, slots=True)
class Predicate:
    """Immutable declarative condition evaluated by a QueryEngine."""


@dataclass(frozen=True, slots=True)
class Equals(Predicate):
    field: str
    value: QueryValue

    def __post_init__(self) -> None:
        object.__setattr__(self, "field", _validate_non_empty(self.field, "field"))
        _validate_query_value(self.value)


@dataclass(frozen=True, slots=True)
class NotEquals(Predicate):
    field: str
    value: QueryValue

    def __post_init__(self) -> None:
        object.__setattr__(self, "field", _validate_non_empty(self.field, "field"))
        _validate_query_value(self.value)


@dataclass(frozen=True, slots=True)
class KindIs(Predicate):
    kind: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", _validate_non_empty(self.kind, "kind"))


@dataclass(frozen=True, slots=True)
class NamespaceIs(Predicate):
    namespace: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "namespace", _validate_non_empty(self.namespace, "namespace")
        )


@dataclass(frozen=True, slots=True)
class HasRelation(Predicate):
    relation_kind: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "relation_kind",
            _validate_non_empty(self.relation_kind, "relation_kind"),
        )


@dataclass(frozen=True, slots=True)
class HasEvidence(Predicate):
    evidence_kind: str | None = None

    def __post_init__(self) -> None:
        if self.evidence_kind is not None:
            object.__setattr__(
                self,
                "evidence_kind",
                _validate_non_empty(self.evidence_kind, "evidence_kind"),
            )


@dataclass(frozen=True, slots=True)
class HasTransformation(Predicate):
    transformation_kind: str | None = None

    def __post_init__(self) -> None:
        if self.transformation_kind is not None:
            object.__setattr__(
                self,
                "transformation_kind",
                _validate_non_empty(self.transformation_kind, "transformation_kind"),
            )


@dataclass(frozen=True, slots=True)
class And(Predicate):
    predicates: tuple[Predicate, ...]

    def __post_init__(self) -> None:
        if len(self.predicates) < 2:
            raise ValueError("And requires at least two predicates")


@dataclass(frozen=True, slots=True)
class Or(Predicate):
    predicates: tuple[Predicate, ...]

    def __post_init__(self) -> None:
        if len(self.predicates) < 2:
            raise ValueError("Or requires at least two predicates")


@dataclass(frozen=True, slots=True)
class Not(Predicate):
    predicate: Predicate


@dataclass(frozen=True, slots=True)
class Traversal:
    """Immutable traversal intent; traversal algorithms belong to QueryEngine."""


@dataclass(frozen=True, slots=True)
class Parents(Traversal):
    pass


@dataclass(frozen=True, slots=True)
class Children(Traversal):
    pass


@dataclass(frozen=True, slots=True)
class Neighbors(Traversal):
    relation_kind: str | None = None

    def __post_init__(self) -> None:
        if self.relation_kind is not None:
            object.__setattr__(
                self,
                "relation_kind",
                _validate_non_empty(self.relation_kind, "relation_kind"),
            )


@dataclass(frozen=True, slots=True)
class Ancestors(Traversal):
    max_depth: int | None = None

    def __post_init__(self) -> None:
        if self.max_depth is not None and self.max_depth < 1:
            raise ValueError("max_depth must be at least 1")


@dataclass(frozen=True, slots=True)
class Descendants(Traversal):
    max_depth: int | None = None

    def __post_init__(self) -> None:
        if self.max_depth is not None and self.max_depth < 1:
            raise ValueError("max_depth must be at least 1")


@dataclass(frozen=True, slots=True)
class ShortestPath(Traversal):
    target: KIRIdentity
    relation_kind: str | None = None

    def __post_init__(self) -> None:
        if self.relation_kind is not None:
            object.__setattr__(
                self,
                "relation_kind",
                _validate_non_empty(self.relation_kind, "relation_kind"),
            )


class OrderingDirection(StrEnum):
    ASCENDING = "ascending"
    DESCENDING = "descending"


@dataclass(frozen=True, slots=True)
class Ordering:
    field: str
    direction: OrderingDirection = OrderingDirection.ASCENDING

    def __post_init__(self) -> None:
        object.__setattr__(self, "field", _validate_non_empty(self.field, "field"))


@dataclass(frozen=True, slots=True)
class Projection:
    fields: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        normalized = tuple(_validate_non_empty(item, "projection field") for item in self.fields)
        if len(set(normalized)) != len(normalized):
            raise ValueError("projection fields must be unique")
        object.__setattr__(self, "fields", normalized)


@dataclass(frozen=True, slots=True)
class Pagination:
    offset: int = 0
    limit: int | None = None

    def __post_init__(self) -> None:
        if self.offset < 0:
            raise ValueError("offset must not be negative")
        if self.limit is not None and self.limit < 1:
            raise ValueError("limit must be at least 1")


@dataclass(frozen=True, slots=True)
class Query:
    """Storage-independent, immutable description of a KIR graph query."""

    origin: tuple[KIRIdentity, ...] = field(default_factory=tuple)
    predicate: Predicate | None = None
    traversal: Traversal | None = None
    ordering: tuple[Ordering, ...] = field(default_factory=tuple)
    projection: Projection = field(default_factory=Projection)
    pagination: Pagination = field(default_factory=Pagination)

    def __post_init__(self) -> None:
        if len(set(self.origin)) != len(self.origin):
            raise ValueError("origin identities must be unique")
        ordering_fields = tuple(item.field for item in self.ordering)
        if len(set(ordering_fields)) != len(ordering_fields):
            raise ValueError("each ordering field may occur only once")
        if self.traversal is not None and not self.origin:
            raise ValueError("traversal queries require at least one origin identity")

    def where(self, predicate: Predicate) -> Query:
        """Return a new query with the predicate composed using And."""

        composed = predicate if self.predicate is None else And((self.predicate, predicate))
        return replace(self, predicate=composed)

    def project(self, *fields: str) -> Query:
        """Return a new query with an explicit projection."""

        return replace(self, projection=Projection(tuple(fields)))

    def order_by(self, *ordering: Ordering) -> Query:
        """Return a new query with deterministic ordering declarations."""

        return replace(self, ordering=tuple(ordering))

    def paginate(self, *, offset: int = 0, limit: int | None = None) -> Query:
        """Return a new query with pagination parameters."""

        return replace(self, pagination=Pagination(offset, limit))


@dataclass(frozen=True, slots=True)
class QueryResult:
    """Immutable result produced by a QueryEngine execution."""

    elements: tuple[Any, ...] = field(default_factory=tuple)
    metadata: tuple[ResultEntry, ...] = field(default_factory=tuple)
    statistics: tuple[ResultEntry, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", _normalize_entries(self.metadata, "metadata"))
        object.__setattr__(self, "statistics", _normalize_entries(self.statistics, "statistics"))

    def metadata_value(self, key: str, default: QueryValue = None) -> QueryValue:
        for entry_key, value in self.metadata:
            if entry_key == key:
                return value
        return default

    def statistic(self, key: str, default: QueryValue = None) -> QueryValue:
        for entry_key, value in self.statistics:
            if entry_key == key:
                return value
        return default


class QueryEngine(ABC):
    """Backend-neutral execution contract for declarative KIR queries."""

    @abstractmethod
    def execute(self, query: Query) -> QueryResult:
        """Execute a query without mutating it and return a deterministic result."""
