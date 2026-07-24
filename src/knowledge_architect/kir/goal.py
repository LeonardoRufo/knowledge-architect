from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol, TypeAlias, runtime_checkable

from .identity import KIRIdentity
from .query import Query, QueryResult
from .versioning import SnapshotId

GoalValue: TypeAlias = str | int | float | bool | None
GoalMetadataEntry: TypeAlias = tuple[str, GoalValue]


class GoalId(KIRIdentity):
    prefix = "goal"


class GoalStatus(StrEnum):
    PENDING = "pending"
    SATISFIED = "satisfied"
    FAILED = "failed"
    BLOCKED = "blocked"


class GoalPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


def _non_empty(value: str, name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} must not be empty")
    return normalized


def _entries(
    values: Mapping[str, GoalValue] | tuple[GoalMetadataEntry, ...] | None,
    name: str,
) -> tuple[GoalMetadataEntry, ...]:
    if values is None:
        return ()
    materialized = tuple(values.items()) if isinstance(values, Mapping) else tuple(values)
    result: list[GoalMetadataEntry] = []
    seen: set[str] = set()
    for key, value in materialized:
        key = _non_empty(key, f"{name} key")
        if key in seen:
            raise ValueError(f"{name} keys must be unique")
        if value is not None and not isinstance(value, (str, int, float, bool)):
            raise TypeError(f"{name} values must be primitive")
        seen.add(key)
        result.append((key, value))
    return tuple(sorted(result, key=lambda item: item[0]))


@dataclass(frozen=True, slots=True)
class GoalConstraint:
    name: str
    value: GoalValue

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _non_empty(self.name, "constraint name"))
        if self.value is not None and not isinstance(self.value, (str, int, float, bool)):
            raise TypeError("constraint value must be primitive")


@dataclass(frozen=True, slots=True)
class GoalCriterion:
    query: Query
    minimum_count: int = 1
    description: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.query, Query):
            raise TypeError("query must be a Query")
        if self.minimum_count < 0:
            raise ValueError("minimum_count must not be negative")
        if self.description is not None:
            object.__setattr__(
                self, "description", _non_empty(self.description, "criterion description")
            )


@dataclass(frozen=True, slots=True)
class GoalDependency:
    goal_id: GoalId
    required_status: GoalStatus = GoalStatus.SATISFIED


@dataclass(frozen=True, slots=True)
class Goal:
    id: GoalId
    description: str
    criteria: tuple[GoalCriterion, ...]
    constraints: tuple[GoalConstraint, ...] = field(default_factory=tuple)
    dependencies: tuple[GoalDependency, ...] = field(default_factory=tuple)
    components: tuple[GoalId, ...] = field(default_factory=tuple)
    priority: GoalPriority = GoalPriority.NORMAL
    metadata: tuple[GoalMetadataEntry, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "description", _non_empty(self.description, "description"))
        if not self.criteria and not self.components:
            raise ValueError("goal requires at least one criterion or component")
        dependency_ids = tuple(item.goal_id for item in self.dependencies)
        if len(set(dependency_ids)) != len(dependency_ids):
            raise ValueError("goal dependencies must be unique")
        if self.id in dependency_ids or self.id in self.components:
            raise ValueError("goal cannot depend on or contain itself")
        if len(set(self.components)) != len(self.components):
            raise ValueError("goal components must be unique")
        object.__setattr__(self, "metadata", _entries(self.metadata, "metadata"))


@dataclass(frozen=True, slots=True)
class GoalEvaluation:
    goal: Goal
    status: GoalStatus
    evaluated_at: datetime
    justification: str
    criterion_results: tuple[QueryResult, ...] = field(default_factory=tuple)
    snapshot_id: SnapshotId | None = None

    def __post_init__(self) -> None:
        if self.evaluated_at.tzinfo is None:
            raise ValueError("evaluated_at must be timezone-aware")
        object.__setattr__(
            self, "justification", _non_empty(self.justification, "justification")
        )


@runtime_checkable
class GoalQuerySource(Protocol):
    def query(self, query: Query, **kwargs: object) -> QueryResult: ...


class InMemoryGoalEvaluator:
    """Deterministic evaluator for immutable goals over a query-capable source."""

    def __init__(self, source: GoalQuerySource) -> None:
        if not isinstance(source, GoalQuerySource):
            raise TypeError("source must provide query(query)")
        self._source = source

    def evaluate(
        self,
        goal: Goal,
        *,
        dependency_evaluations: Iterable[GoalEvaluation] = (),
        snapshot_id: SnapshotId | None = None,
        evaluated_at: datetime | None = None,
    ) -> GoalEvaluation:
        dependencies = {item.goal.id: item for item in dependency_evaluations}
        blocked = tuple(
            dependency
            for dependency in goal.dependencies
            if dependency.goal_id not in dependencies
            or dependencies[dependency.goal_id].status is not dependency.required_status
        )
        timestamp = evaluated_at or datetime.now(UTC)
        if blocked:
            identifiers = ", ".join(str(item.goal_id) for item in blocked)
            return GoalEvaluation(
                goal,
                GoalStatus.BLOCKED,
                timestamp,
                f"unsatisfied dependencies: {identifiers}",
                snapshot_id=snapshot_id,
            )

        results = tuple(
            self._execute(criterion.query, snapshot_id) for criterion in goal.criteria
        )
        failures = tuple(
            index
            for index, (criterion, result) in enumerate(zip(goal.criteria, results, strict=True), 1)
            if len(result.elements) < criterion.minimum_count
        )
        if failures:
            numbers = ", ".join(str(item) for item in failures)
            return GoalEvaluation(
                goal,
                GoalStatus.FAILED,
                timestamp,
                f"criteria not satisfied: {numbers}",
                results,
                snapshot_id,
            )
        return GoalEvaluation(
            goal,
            GoalStatus.SATISFIED,
            timestamp,
            "all criteria satisfied",
            results,
            snapshot_id,
        )

    def _execute(self, query: Query, snapshot_id: SnapshotId | None) -> QueryResult:
        if snapshot_id is None:
            return self._source.query(query)
        try:
            return self._source.query(query, snapshot_id=snapshot_id)
        except TypeError as exc:
            raise TypeError("query source does not support snapshot evaluation") from exc

    @staticmethod
    def validate_dependencies(goals: Iterable[Goal]) -> bool:
        graph = {goal.id: tuple(item.goal_id for item in goal.dependencies) for goal in goals}
        visiting: set[GoalId] = set()
        visited: set[GoalId] = set()

        def visit(goal_id: GoalId) -> None:
            if goal_id in visiting:
                raise ValueError("goal dependencies must not contain cycles")
            if goal_id in visited:
                return
            visiting.add(goal_id)
            for dependency_id in graph.get(goal_id, ()):
                if dependency_id in graph:
                    visit(dependency_id)
            visiting.remove(goal_id)
            visited.add(goal_id)

        for identifier in sorted(graph, key=str):
            visit(identifier)
        return True
