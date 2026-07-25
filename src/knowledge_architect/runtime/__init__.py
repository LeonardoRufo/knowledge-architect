from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from enum import StrEnum
from threading import RLock
from types import MappingProxyType
from typing import Any, TypeAlias
from uuid import UUID, uuid4

from knowledge_architect.kir import (
    PlanRevision,
    PlanStep,
    PlanStepId,
    QueryEngine,
    RevisionId,
    SnapshotId,
    TransformationId,
)

RuntimeValue: TypeAlias = str | int | float | bool | None
StepHandler: TypeAlias = Callable[[PlanStep, "RuntimeContext"], "StepOutcome"]
Clock: TypeAlias = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class ExecutionId:
    value: str

    def __post_init__(self) -> None:
        if not self.value.startswith("execution:"):
            raise ValueError("ExecutionId must start with 'execution:'")
        UUID(self.value.removeprefix("execution:"))

    @classmethod
    def new(cls) -> ExecutionId:
        return cls(f"execution:{uuid4()}")

    def __str__(self) -> str:
        return self.value


class ExecutionState(StrEnum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"

    @property
    def terminal(self) -> bool:
        return self in {
            ExecutionState.SUCCEEDED,
            ExecutionState.FAILED,
            ExecutionState.BLOCKED,
            ExecutionState.CANCELLED,
        }


class ExecutionError(Exception):
    pass


class ExecutionNotFoundError(ExecutionError):
    pass


class InvalidExecutionTransitionError(ExecutionError):
    pass


class ExecutionAlreadyExistsError(ExecutionError):
    pass


@dataclass(frozen=True, slots=True)
class RuntimeContext:
    snapshot_id: SnapshotId | None = None
    plan_revision_id: RevisionId | None = None
    goal_revision_ids: tuple[RevisionId, ...] = field(default_factory=tuple)
    variables: Mapping[str, RuntimeValue] = field(default_factory=dict)
    parameters: Mapping[str, RuntimeValue] = field(default_factory=dict)
    configuration: Mapping[str, RuntimeValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "variables", MappingProxyType(dict(self.variables)))
        object.__setattr__(self, "parameters", MappingProxyType(dict(self.parameters)))
        object.__setattr__(self, "configuration", MappingProxyType(dict(self.configuration)))
        if len(set(self.goal_revision_ids)) != len(self.goal_revision_ids):
            raise ValueError("goal revision references must be unique")


@dataclass(frozen=True, slots=True)
class StepOutcome:
    result: Any = None
    transformation_ids: tuple[TransformationId, ...] = field(default_factory=tuple)
    metrics: tuple[tuple[str, RuntimeValue], ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class ExecutionEvent:
    execution_id: ExecutionId
    sequence: int
    occurred_at: datetime
    event_type: str
    state: ExecutionState
    step_id: PlanStepId | None = None
    result: Any = None
    error: str | None = None
    transformation_ids: tuple[TransformationId, ...] = field(default_factory=tuple)
    metrics: tuple[tuple[str, RuntimeValue], ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.sequence < 1:
            raise ValueError("event sequence must be positive")
        if self.occurred_at.tzinfo is None:
            raise ValueError("event timestamp must be timezone-aware")
        if not self.event_type.strip():
            raise ValueError("event_type must not be empty")


@dataclass(frozen=True, slots=True)
class StepExecution:
    step_id: PlanStepId
    state: ExecutionState = ExecutionState.PENDING
    started_at: datetime | None = None
    ended_at: datetime | None = None
    result: Any = None
    error: str | None = None
    transformation_ids: tuple[TransformationId, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class PlanExecution:
    id: ExecutionId
    plan_id: Any
    plan_revision_id: RevisionId
    goal_revision_ids: tuple[RevisionId, ...]
    snapshot_id: SnapshotId | None
    state: ExecutionState
    steps: tuple[StepExecution, ...]
    created_at: datetime
    started_at: datetime | None = None
    ended_at: datetime | None = None

    def step(self, step_id: PlanStepId) -> StepExecution:
        for step in self.steps:
            if step.step_id == step_id:
                return step
        raise KeyError(step_id)


@dataclass(frozen=True, slots=True)
class ExecutionHistory:
    execution_id: ExecutionId
    events: tuple[ExecutionEvent, ...]

    def __post_init__(self) -> None:
        expected = tuple(range(1, len(self.events) + 1))
        actual = tuple(event.sequence for event in self.events)
        if actual != expected:
            raise ValueError("execution history sequence must be contiguous")
        if any(event.execution_id != self.execution_id for event in self.events):
            raise ValueError("all events must belong to the same execution")


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    execution_id: ExecutionId
    state: ExecutionState
    success: bool
    duration_seconds: float
    events: tuple[ExecutionEvent, ...]
    metrics: tuple[tuple[str, RuntimeValue], ...] = field(default_factory=tuple)


class ExecutionEngine(ABC):
    @abstractmethod
    def execute(self, plan_revision: PlanRevision, context: RuntimeContext) -> ExecutionResult:
        raise NotImplementedError

    @abstractmethod
    def resume(self, execution_id: ExecutionId) -> ExecutionResult:
        raise NotImplementedError

    @abstractmethod
    def cancel(self, execution_id: ExecutionId) -> ExecutionResult:
        raise NotImplementedError


Runtime = ExecutionEngine


class InMemoryRuntime(ExecutionEngine):
    """Synchronous, deterministic and thread-safe event-sourced runtime."""

    def __init__(
        self,
        *,
        query_engine: QueryEngine | None = None,
        step_handler: StepHandler | None = None,
        clock: Clock = _utc_now,
    ) -> None:
        self._query_engine = query_engine
        self._step_handler = step_handler or (lambda _step, _context: StepOutcome())
        self._clock = clock
        self._lock = RLock()
        self._plans: dict[ExecutionId, PlanRevision] = {}
        self._contexts: dict[ExecutionId, RuntimeContext] = {}
        self._events: dict[ExecutionId, list[ExecutionEvent]] = {}

    def execute(self, plan_revision: PlanRevision, context: RuntimeContext) -> ExecutionResult:
        with self._lock:
            execution_id = ExecutionId.new()
            effective = replace(context, plan_revision_id=plan_revision.revision_id)
            self._plans[execution_id] = plan_revision
            self._contexts[execution_id] = effective
            self._events[execution_id] = []
            self._append(execution_id, "ExecutionCreated", ExecutionState.PENDING)
            self._append(execution_id, "ExecutionStarted", ExecutionState.RUNNING)
            return self._run(execution_id)

    def resume(self, execution_id: ExecutionId) -> ExecutionResult:
        with self._lock:
            execution = self.get_execution(execution_id)
            if execution.state.terminal:
                return self._result(execution_id)
            self._append(execution_id, "ExecutionResumed", ExecutionState.RUNNING)
            return self._run(execution_id)

    def cancel(self, execution_id: ExecutionId) -> ExecutionResult:
        with self._lock:
            execution = self.get_execution(execution_id)
            if execution.state.terminal:
                raise InvalidExecutionTransitionError("terminal executions cannot be cancelled")
            self._append(execution_id, "ExecutionCancelled", ExecutionState.CANCELLED)
            return self._result(execution_id)

    def history(self, execution_id: ExecutionId) -> ExecutionHistory:
        with self._lock:
            try:
                return ExecutionHistory(execution_id, tuple(self._events[execution_id]))
            except KeyError as exc:
                raise ExecutionNotFoundError(str(execution_id)) from exc

    def get_execution(self, execution_id: ExecutionId) -> PlanExecution:
        with self._lock:
            plan_revision = self._plan(execution_id)
            events = tuple(self._events[execution_id])
            return self.reconstruct(plan_revision, self._contexts[execution_id], events)

    @staticmethod
    def reconstruct(
        plan_revision: PlanRevision,
        context: RuntimeContext,
        events: tuple[ExecutionEvent, ...],
    ) -> PlanExecution:
        if not events:
            raise ValueError("at least one event is required")
        created_at = events[0].occurred_at
        state = events[-1].state
        step_map = {step.id: StepExecution(step.id) for step in plan_revision.plan.graph.steps}
        started_at = None
        ended_at = None
        for event in events:
            if event.event_type in {"ExecutionStarted", "ExecutionResumed"} and started_at is None:
                started_at = event.occurred_at
            if event.event_type in {"ExecutionCompleted", "ExecutionFailed", "ExecutionBlocked", "ExecutionCancelled"}:
                ended_at = event.occurred_at
            if event.step_id is None:
                continue
            current = step_map[event.step_id]
            if event.event_type == "StepReady":
                current = replace(current, state=ExecutionState.READY)
            elif event.event_type == "StepStarted":
                current = replace(current, state=ExecutionState.RUNNING, started_at=event.occurred_at)
            elif event.event_type == "StepCompleted":
                current = replace(current, state=ExecutionState.SUCCEEDED, ended_at=event.occurred_at, result=event.result, transformation_ids=event.transformation_ids)
            elif event.event_type == "StepFailed":
                current = replace(current, state=ExecutionState.FAILED, ended_at=event.occurred_at, error=event.error)
            elif event.event_type == "StepBlocked":
                current = replace(current, state=ExecutionState.BLOCKED, ended_at=event.occurred_at, error=event.error)
            step_map[event.step_id] = current
        ordered = tuple(step_map[step.id] for step in plan_revision.plan.graph.steps)
        return PlanExecution(
            events[0].execution_id,
            plan_revision.plan.id,
            plan_revision.revision_id,
            context.goal_revision_ids,
            context.snapshot_id,
            state,
            ordered,
            created_at,
            started_at,
            ended_at,
        )

    def _run(self, execution_id: ExecutionId) -> ExecutionResult:
        plan_revision = self._plan(execution_id)
        plan = plan_revision.plan
        context = self._contexts[execution_id]
        for step_id in plan.graph.topological_order():
            current = self.get_execution(execution_id).step(step_id)
            if current.state == ExecutionState.SUCCEEDED:
                continue
            step = plan.graph.step(step_id)
            dependencies = [self.get_execution(execution_id).step(item.step_id) for item in step.dependencies]
            if any(item.state != ExecutionState.SUCCEEDED for item in dependencies):
                self._append(execution_id, "StepBlocked", ExecutionState.BLOCKED, step_id=step.id, error="dependencies are not satisfied")
                self._append(execution_id, "ExecutionBlocked", ExecutionState.BLOCKED)
                return self._result(execution_id)
            if not self._conditions_satisfied(step.preconditions):
                self._append(execution_id, "StepBlocked", ExecutionState.BLOCKED, step_id=step.id, error="preconditions are not satisfied")
                self._append(execution_id, "ExecutionBlocked", ExecutionState.BLOCKED)
                return self._result(execution_id)
            self._append(execution_id, "StepReady", ExecutionState.READY, step_id=step.id)
            self._append(execution_id, "StepStarted", ExecutionState.RUNNING, step_id=step.id)
            try:
                outcome = self._step_handler(step, context)
                if not isinstance(outcome, StepOutcome):
                    outcome = StepOutcome(outcome)
            except Exception as exc:  # noqa: BLE001
                self._append(execution_id, "StepFailed", ExecutionState.FAILED, step_id=step.id, error=str(exc))
                self._append(execution_id, "ExecutionFailed", ExecutionState.FAILED)
                return self._result(execution_id)
            if not self._conditions_satisfied(step.postconditions) or not self._conditions_satisfied(step.completion_criteria):
                self._append(execution_id, "StepFailed", ExecutionState.FAILED, step_id=step.id, error="postconditions or completion criteria are not satisfied")
                self._append(execution_id, "ExecutionFailed", ExecutionState.FAILED)
                return self._result(execution_id)
            self._append(execution_id, "StepCompleted", ExecutionState.SUCCEEDED, step_id=step.id, result=outcome.result, transformation_ids=outcome.transformation_ids, metrics=outcome.metrics)
        if not self._conditions_satisfied(plan.completion_criteria):
            self._append(execution_id, "ExecutionFailed", ExecutionState.FAILED, error="plan completion criteria are not satisfied")
        else:
            self._append(execution_id, "ExecutionCompleted", ExecutionState.SUCCEEDED)
        return self._result(execution_id)

    def _conditions_satisfied(self, conditions: Any) -> bool:
        for condition in conditions:
            query = getattr(condition, "query", None)
            if query is None:
                continue
            if self._query_engine is None:
                return False
            if len(self._query_engine.execute(query).elements) < condition.minimum_count:
                return False
        return True

    def _append(self, execution_id: ExecutionId, event_type: str, state: ExecutionState, **kwargs: Any) -> ExecutionEvent:
        events = self._events[execution_id]
        event = ExecutionEvent(execution_id, len(events) + 1, self._clock(), event_type, state, **kwargs)
        events.append(event)
        return event

    def _plan(self, execution_id: ExecutionId) -> PlanRevision:
        try:
            return self._plans[execution_id]
        except KeyError as exc:
            raise ExecutionNotFoundError(str(execution_id)) from exc

    def _result(self, execution_id: ExecutionId) -> ExecutionResult:
        execution = self.get_execution(execution_id)
        events = self.history(execution_id).events
        duration = 0.0
        if execution.started_at is not None and execution.ended_at is not None:
            duration = (execution.ended_at - execution.started_at).total_seconds()
        metrics: dict[str, RuntimeValue] = {}
        for event in events:
            metrics.update(event.metrics)
        return ExecutionResult(execution_id, execution.state, execution.state == ExecutionState.SUCCEEDED, duration, events, tuple(sorted(metrics.items())))


__all__ = [
    "ExecutionEngine", "ExecutionError", "ExecutionEvent", "ExecutionHistory",
    "ExecutionId", "ExecutionNotFoundError", "ExecutionResult", "ExecutionState",
    "InMemoryRuntime", "InvalidExecutionTransitionError", "PlanExecution", "Runtime",
    "RuntimeContext", "StepExecution", "StepOutcome",
]
