from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from threading import RLock
from typing import TypeAlias

from .goal import GoalId, GoalPriority
from .identity import KIRIdentity, TransformationId
from .query import Query
from .versioning import RevisionId

PlanValue: TypeAlias = str | int | float | bool | None
PlanMetadataEntry: TypeAlias = tuple[str, PlanValue]


class PlanId(KIRIdentity):
    prefix = "plan"


class PlanStepId(KIRIdentity):
    prefix = "plan-step"


class PlanValidationError(ValueError):
    """Raised when a declarative plan violates structural invariants."""


def _text(value: str, name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} must not be empty")
    return normalized


def _metadata(
    values: Mapping[str, PlanValue] | tuple[PlanMetadataEntry, ...] | None,
) -> tuple[PlanMetadataEntry, ...]:
    if values is None:
        return ()
    items = tuple(values.items()) if isinstance(values, Mapping) else tuple(values)
    result: list[PlanMetadataEntry] = []
    seen: set[str] = set()
    for key, value in items:
        key = _text(key, "metadata key")
        if key in seen:
            raise ValueError("metadata keys must be unique")
        if value is not None and not isinstance(value, (str, int, float, bool)):
            raise TypeError("metadata values must be primitive")
        seen.add(key)
        result.append((key, value))
    return tuple(sorted(result, key=lambda item: item[0]))


@dataclass(frozen=True, slots=True)
class PlanDependency:
    step_id: PlanStepId


@dataclass(frozen=True, slots=True)
class Precondition:
    description: str
    query: Query | None = None
    minimum_count: int = 1

    def __post_init__(self) -> None:
        object.__setattr__(self, "description", _text(self.description, "description"))
        if self.query is not None and not isinstance(self.query, Query):
            raise TypeError("query must be a Query or None")
        if self.minimum_count < 0:
            raise ValueError("minimum_count must not be negative")


@dataclass(frozen=True, slots=True)
class Postcondition:
    description: str
    query: Query | None = None
    minimum_count: int = 1

    def __post_init__(self) -> None:
        object.__setattr__(self, "description", _text(self.description, "description"))
        if self.query is not None and not isinstance(self.query, Query):
            raise TypeError("query must be a Query or None")
        if self.minimum_count < 0:
            raise ValueError("minimum_count must not be negative")


@dataclass(frozen=True, slots=True)
class CompletionCriterion:
    description: str
    query: Query
    minimum_count: int = 1

    def __post_init__(self) -> None:
        object.__setattr__(self, "description", _text(self.description, "description"))
        if not isinstance(self.query, Query):
            raise TypeError("query must be a Query")
        if self.minimum_count < 0:
            raise ValueError("minimum_count must not be negative")


@dataclass(frozen=True, slots=True)
class PlanMetadata:
    author: str | None = None
    version: str | None = None
    domain: str | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)
    priority: GoalPriority = GoalPriority.NORMAL
    entries: tuple[PlanMetadataEntry, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        for name in ("author", "version", "domain"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _text(value, name))
        normalized_tags = tuple(sorted({_text(tag, "tag") for tag in self.tags}))
        object.__setattr__(self, "tags", normalized_tags)
        object.__setattr__(self, "entries", _metadata(self.entries))


@dataclass(frozen=True, slots=True)
class PlanStep:
    id: PlanStepId
    name: str
    description: str
    dependencies: tuple[PlanDependency, ...] = field(default_factory=tuple)
    preconditions: tuple[Precondition, ...] = field(default_factory=tuple)
    postconditions: tuple[Postcondition, ...] = field(default_factory=tuple)
    completion_criteria: tuple[CompletionCriterion, ...] = field(default_factory=tuple)
    subplan_id: PlanId | None = None
    expected_transformations: tuple[TransformationId, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _text(self.name, "step name"))
        object.__setattr__(self, "description", _text(self.description, "step description"))
        dependency_ids = tuple(item.step_id for item in self.dependencies)
        if self.id in dependency_ids:
            raise PlanValidationError("a step cannot depend on itself")
        if len(set(dependency_ids)) != len(dependency_ids):
            raise PlanValidationError("step dependencies must be unique")
        if len(set(self.expected_transformations)) != len(self.expected_transformations):
            raise PlanValidationError("expected transformations must be unique")


@dataclass(frozen=True, slots=True)
class PlanGraph:
    steps: tuple[PlanStep, ...]

    def __post_init__(self) -> None:
        if not self.steps:
            raise PlanValidationError("a plan graph requires at least one step")
        identifiers = tuple(step.id for step in self.steps)
        if len(set(identifiers)) != len(identifiers):
            raise PlanValidationError("plan step identities must be unique")

    def step(self, step_id: PlanStepId) -> PlanStep:
        for item in self.steps:
            if item.id == step_id:
                return item
        raise KeyError(step_id)

    def topological_order(self) -> tuple[PlanStepId, ...]:
        return PlanValidator.topological_order(self)


@dataclass(frozen=True, slots=True)
class Plan:
    id: PlanId
    name: str
    description: str
    goal_ids: tuple[GoalId, ...]
    graph: PlanGraph
    completion_criteria: tuple[CompletionCriterion, ...] = field(default_factory=tuple)
    metadata: PlanMetadata = field(default_factory=PlanMetadata)

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _text(self.name, "plan name"))
        object.__setattr__(self, "description", _text(self.description, "plan description"))
        if not self.goal_ids:
            raise PlanValidationError("a plan must target at least one goal")
        if len(set(self.goal_ids)) != len(self.goal_ids):
            raise PlanValidationError("goal references must be unique")
        PlanValidator.validate(self)


class PlanValidator:
    """Validates references, reachability and acyclicity of immutable plans."""

    @classmethod
    def validate(cls, plan: Plan) -> bool:
        cls.topological_order(plan.graph)
        cls._validate_subplans((plan,))
        return True

    @staticmethod
    def topological_order(graph: PlanGraph) -> tuple[PlanStepId, ...]:
        by_id = {step.id: step for step in graph.steps}
        for step in graph.steps:
            for dependency in step.dependencies:
                if dependency.step_id not in by_id:
                    raise PlanValidationError("dependency references an unknown step")

        visiting: set[PlanStepId] = set()
        visited: set[PlanStepId] = set()
        ordered: list[PlanStepId] = []

        def visit(step_id: PlanStepId) -> None:
            if step_id in visiting:
                raise PlanValidationError("plan graph must be acyclic")
            if step_id in visited:
                return
            visiting.add(step_id)
            dependencies = sorted(
                by_id[step_id].dependencies, key=lambda item: str(item.step_id)
            )
            for dependency in dependencies:
                visit(dependency.step_id)
            visiting.remove(step_id)
            visited.add(step_id)
            ordered.append(step_id)

        for step_id in sorted(by_id, key=str):
            visit(step_id)
        return tuple(ordered)

    @staticmethod
    def _validate_subplans(plans: Iterable[Plan]) -> None:
        materialized = tuple(plans)
        graph = {
            plan.id: tuple(
                step.subplan_id for step in plan.graph.steps if step.subplan_id is not None
            )
            for plan in materialized
        }
        visiting: set[PlanId] = set()
        visited: set[PlanId] = set()

        def visit(plan_id: PlanId) -> None:
            if plan_id in visiting:
                raise PlanValidationError("subplans must not contain cycles")
            if plan_id in visited:
                return
            visiting.add(plan_id)
            for child in graph.get(plan_id, ()):
                if child in graph:
                    visit(child)
            visiting.remove(plan_id)
            visited.add(plan_id)

        for plan_id in sorted(graph, key=str):
            visit(plan_id)

    @classmethod
    def validate_repository(cls, plans: Iterable[Plan]) -> bool:
        materialized = tuple(plans)
        for plan in materialized:
            cls.validate(plan)
        cls._validate_subplans(materialized)
        return True


@dataclass(frozen=True, slots=True)
class PlanRevision:
    revision_id: RevisionId
    plan: Plan
    revision_number: int
    previous_revision_id: RevisionId | None = None


class PlanRepositoryError(Exception):
    pass


class PlanConflictError(PlanRepositoryError):
    pass


class PlanNotFoundError(PlanRepositoryError):
    pass


class InMemoryPlanRepository:
    """Thread-safe reference repository with immutable linear plan revisions."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._current: dict[PlanId, RevisionId] = {}
        self._revisions: dict[RevisionId, PlanRevision] = {}
        self._history: dict[PlanId, list[RevisionId]] = {}

    def save(
        self, plan: Plan, *, expected_revision_id: RevisionId | None = None
    ) -> PlanRevision:
        PlanValidator.validate(plan)
        with self._lock:
            current = self._current.get(plan.id)
            if current is not None and expected_revision_id is None:
                raise PlanConflictError("updating a plan requires expected_revision_id")
            if current != expected_revision_id:
                raise PlanConflictError("expected plan revision does not match current revision")
            current_plans = {
                identifier: self._revisions[revision_id].plan
                for identifier, revision_id in self._current.items()
            }
            current_plans[plan.id] = plan
            PlanValidator.validate_repository(current_plans.values())
            history = self._history.setdefault(plan.id, [])
            revision = PlanRevision(
                RevisionId.new(),
                plan,
                len(history) + 1,
                current,
            )
            history.append(revision.revision_id)
            self._revisions[revision.revision_id] = revision
            self._current[plan.id] = revision.revision_id
            return revision

    def load(self, plan_id: PlanId) -> Plan:
        return self.load_revision_record(self._current_id(plan_id)).plan

    def load_revision_record(self, revision_id: RevisionId) -> PlanRevision:
        with self._lock:
            try:
                return self._revisions[revision_id]
            except KeyError as exc:
                raise PlanNotFoundError(f"plan revision not found: {revision_id}") from exc

    def history(self, plan_id: PlanId) -> tuple[PlanRevision, ...]:
        with self._lock:
            if plan_id not in self._history:
                raise PlanNotFoundError(f"plan not found: {plan_id}")
            return tuple(self._revisions[item] for item in self._history[plan_id])

    def list(self, *, goal_id: GoalId | None = None) -> tuple[PlanRevision, ...]:
        with self._lock:
            records = tuple(self._revisions[item] for item in self._current.values())
        if goal_id is not None:
            records = tuple(item for item in records if goal_id in item.plan.goal_ids)
        return tuple(sorted(records, key=lambda item: str(item.plan.id)))

    def alternatives(self, goal_id: GoalId) -> tuple[Plan, ...]:
        return tuple(record.plan for record in self.list(goal_id=goal_id))

    def delete(self, plan_id: PlanId, *, expected_revision_id: RevisionId) -> None:
        with self._lock:
            current = self._current_id(plan_id)
            if current != expected_revision_id:
                raise PlanConflictError("expected plan revision does not match current revision")
            del self._current[plan_id]

    def _current_id(self, plan_id: PlanId) -> RevisionId:
        with self._lock:
            try:
                return self._current[plan_id]
            except KeyError as exc:
                raise PlanNotFoundError(f"plan not found: {plan_id}") from exc
