from datetime import UTC, datetime, timedelta

import pytest

from knowledge_architect.kir import (
    CompletionCriterion,
    GoalId,
    Plan,
    PlanDependency,
    PlanGraph,
    PlanId,
    PlanRevision,
    PlanStep,
    PlanStepId,
    Precondition,
    Query,
    QueryEngine,
    QueryResult,
    RevisionId,
)
from knowledge_architect.runtime import (
    ExecutionEvent,
    ExecutionId,
    ExecutionState,
    InMemoryRuntime,
    InvalidExecutionTransitionError,
    RuntimeContext,
    StepOutcome,
)


class StaticQueryEngine(QueryEngine):
    def __init__(self, count: int) -> None:
        self.count = count

    def execute(self, query: Query) -> QueryResult:
        return QueryResult(tuple(range(self.count)))


def revision(*, with_condition: bool = False) -> PlanRevision:
    a_id, b_id = PlanStepId.new(), PlanStepId.new()
    a = PlanStep(a_id, "A", "first", preconditions=(Precondition("ok", Query(), 1),) if with_condition else ())
    b = PlanStep(b_id, "B", "second", dependencies=(PlanDependency(a_id),))
    plan = Plan(PlanId.new(), "Plan", "runtime plan", (GoalId.new(),), PlanGraph((a, b)))
    return PlanRevision(RevisionId.new(), plan, 1)


def clock():
    current = datetime(2026, 7, 24, tzinfo=UTC)
    def now():
        nonlocal current
        value = current
        current += timedelta(seconds=1)
        return value
    return now


def test_runtime_executes_dag_and_preserves_plan() -> None:
    record = revision()
    original = record.plan
    runtime = InMemoryRuntime(clock=clock(), step_handler=lambda step, ctx: StepOutcome(result=step.name))
    result = runtime.execute(record, RuntimeContext())
    execution = runtime.get_execution(result.execution_id)
    assert result.success is True
    assert execution.state == ExecutionState.SUCCEEDED
    assert all(step.state == ExecutionState.SUCCEEDED for step in execution.steps)
    assert record.plan == original
    assert [event.sequence for event in result.events] == list(range(1, len(result.events) + 1))


def test_precondition_blocks_execution() -> None:
    runtime = InMemoryRuntime(query_engine=StaticQueryEngine(0), clock=clock())
    result = runtime.execute(revision(with_condition=True), RuntimeContext())
    assert result.state == ExecutionState.BLOCKED
    assert any(event.event_type == "StepBlocked" for event in result.events)


def test_handler_failure_is_recorded() -> None:
    def fail(step, context):
        raise RuntimeError("boom")
    runtime = InMemoryRuntime(step_handler=fail, clock=clock())
    result = runtime.execute(revision(), RuntimeContext())
    assert result.state == ExecutionState.FAILED
    assert any(event.error == "boom" for event in result.events)


def test_history_reconstructs_same_execution() -> None:
    record = revision()
    runtime = InMemoryRuntime(clock=clock())
    result = runtime.execute(record, RuntimeContext())
    reconstructed = runtime.reconstruct(record, RuntimeContext(plan_revision_id=record.revision_id), result.events)
    assert reconstructed.state == ExecutionState.SUCCEEDED
    assert reconstructed.id == result.execution_id


def test_terminal_execution_cannot_be_cancelled() -> None:
    runtime = InMemoryRuntime(clock=clock())
    result = runtime.execute(revision(), RuntimeContext())
    with pytest.raises(InvalidExecutionTransitionError):
        runtime.cancel(result.execution_id)


def test_events_are_immutable_and_validate_timestamp() -> None:
    with pytest.raises(ValueError, match="timezone"):
        ExecutionEvent(
            ExecutionId.new(),
            1,
            datetime.now(),  # noqa: DTZ005
            "X",
            ExecutionState.PENDING,
        )


def test_completion_criteria_failure_fails_step() -> None:
    step = PlanStep(PlanStepId.new(), "Only", "only", completion_criteria=(CompletionCriterion("need one", Query(), 1),))
    plan = Plan(PlanId.new(), "P", "D", (GoalId.new(),), PlanGraph((step,)))
    record = PlanRevision(RevisionId.new(), plan, 1)
    runtime = InMemoryRuntime(query_engine=StaticQueryEngine(0), clock=clock())
    result = runtime.execute(record, RuntimeContext())
    assert result.state == ExecutionState.FAILED
