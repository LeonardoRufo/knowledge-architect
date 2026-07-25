from dataclasses import FrozenInstanceError, replace

import pytest

from knowledge_architect.kir import (
    CompletionCriterion,
    GoalId,
    InMemoryPlanRepository,
    KindIs,
    Plan,
    PlanConflictError,
    PlanDependency,
    PlanGraph,
    PlanId,
    PlanMetadata,
    PlanStep,
    PlanStepId,
    PlanValidationError,
    PlanValidator,
    Precondition,
    Query,
    canonical_json,
)


def make_plan(*, goal_id: GoalId | None = None, subplan_id: PlanId | None = None) -> Plan:
    goal_id = goal_id or GoalId.new()
    collect_id = PlanStepId.new()
    validate_id = PlanStepId.new()
    collect = PlanStep(
        collect_id,
        "Collect",
        "Collect source knowledge",
        preconditions=(Precondition("Store is queryable", Query(), 0),),
        subplan_id=subplan_id,
    )
    validate = PlanStep(
        validate_id,
        "Validate",
        "Validate coverage",
        dependencies=(PlanDependency(collect_id),),
        completion_criteria=(
            CompletionCriterion("At least one entity", Query(predicate=KindIs("entity"))),
        ),
    )
    return Plan(
        PlanId.new(),
        "Scientific summary",
        "Produce and validate a scientific summary",
        (goal_id,),
        PlanGraph((validate, collect)),
        metadata=PlanMetadata(author="architect", tags=("science", "summary")),
    )


def test_plan_is_immutable_and_canonically_serializable() -> None:
    plan = make_plan()
    assert canonical_json(plan) == canonical_json(plan)
    with pytest.raises(FrozenInstanceError):
        plan.name = "changed"  # type: ignore[misc]


def test_graph_has_deterministic_topological_order() -> None:
    plan = make_plan()
    order = plan.graph.topological_order()
    collect, validate = plan.graph.steps[1].id, plan.graph.steps[0].id
    assert order.index(collect) < order.index(validate)


def test_unknown_dependency_is_rejected() -> None:
    step = PlanStep(
        PlanStepId.new(),
        "Bad",
        "Unknown dependency",
        dependencies=(PlanDependency(PlanStepId.new()),),
    )
    with pytest.raises(PlanValidationError, match="unknown"):
        Plan(
            PlanId.new(),
            "Bad plan",
            "Invalid graph",
            (GoalId.new(),),
            PlanGraph((step,)),
        )


def test_dependency_cycle_is_rejected() -> None:
    first_id, second_id = PlanStepId.new(), PlanStepId.new()
    first = PlanStep(first_id, "First", "First", (PlanDependency(second_id),))
    second = PlanStep(second_id, "Second", "Second", (PlanDependency(first_id),))
    with pytest.raises(PlanValidationError, match="acyclic"):
        Plan(
            PlanId.new(),
            "Cyclic",
            "Cyclic graph",
            (GoalId.new(),),
            PlanGraph((first, second)),
        )


def test_repository_preserves_linear_plan_versions() -> None:
    repository = InMemoryPlanRepository()
    plan = make_plan()
    first = repository.save(plan)
    updated = replace(plan, description="Updated strategy")
    second = repository.save(updated, expected_revision_id=first.revision_id)
    assert second.revision_number == 2
    assert second.previous_revision_id == first.revision_id
    assert repository.history(plan.id) == (first, second)
    assert repository.load(plan.id) == updated


def test_repository_rejects_silent_overwrite() -> None:
    repository = InMemoryPlanRepository()
    plan = make_plan()
    repository.save(plan)
    with pytest.raises(PlanConflictError):
        repository.save(replace(plan, description="unsafe update"))


def test_multiple_plans_can_target_the_same_goal() -> None:
    goal_id = GoalId.new()
    repository = InMemoryPlanRepository()
    first = make_plan(goal_id=goal_id)
    second = make_plan(goal_id=goal_id)
    repository.save(first)
    repository.save(second)
    assert repository.alternatives(goal_id) == tuple(
        sorted((first, second), key=lambda item: str(item.id))
    )


def test_subplan_cycles_are_rejected_across_repository() -> None:
    repository = InMemoryPlanRepository()
    first_id, second_id = PlanId.new(), PlanId.new()
    first = replace(make_plan(subplan_id=second_id), id=first_id)
    second = replace(make_plan(subplan_id=first_id), id=second_id)
    repository.save(first)
    with pytest.raises(PlanValidationError, match="subplans"):
        PlanValidator.validate_repository((first, second))
