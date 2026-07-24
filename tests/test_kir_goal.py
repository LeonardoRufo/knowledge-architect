from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from knowledge_architect.kir import (
    Entity,
    EntityId,
    Goal,
    GoalConstraint,
    GoalCriterion,
    GoalDependency,
    GoalId,
    GoalPriority,
    GoalStatus,
    InMemoryGoalEvaluator,
    InMemoryKnowledgeStore,
    InMemoryVersionedKnowledgeStore,
    KindIs,
    Query,
    RevisionStatus,
    canonical_json,
)


def make_goal(*, minimum_count: int = 1, dependencies=()) -> Goal:
    return Goal(
        GoalId.new(),
        "Have concepts in the knowledge store",
        (GoalCriterion(Query(predicate=KindIs("entity")), minimum_count),),
        constraints=(GoalConstraint("language", "en"),),
        dependencies=dependencies,
        priority=GoalPriority.HIGH,
        metadata=(("owner", "agent"),),
    )


def test_goal_is_immutable_and_canonically_serializable() -> None:
    goal = make_goal()
    assert canonical_json(goal) == canonical_json(goal)
    with pytest.raises(FrozenInstanceError):
        goal.description = "changed"  # type: ignore[misc]


def test_goal_requires_criterion_or_component() -> None:
    with pytest.raises(ValueError):
        Goal(GoalId.new(), "empty", ())


def test_evaluator_satisfies_query_criterion_deterministically() -> None:
    store = InMemoryKnowledgeStore()
    store.save(Entity(EntityId.new(), "concept", "Depression"))
    evaluator = InMemoryGoalEvaluator(store)
    instant = datetime(2026, 7, 24, tzinfo=UTC)
    first = evaluator.evaluate(make_goal(), evaluated_at=instant)
    second = evaluator.evaluate(first.goal, evaluated_at=instant)
    assert first == second
    assert first.status is GoalStatus.SATISFIED
    assert first.criterion_results[0].elements


def test_evaluator_fails_when_minimum_count_is_not_reached() -> None:
    evaluation = InMemoryGoalEvaluator(InMemoryKnowledgeStore()).evaluate(make_goal())
    assert evaluation.status is GoalStatus.FAILED
    assert evaluation.justification == "criteria not satisfied: 1"


def test_dependency_blocks_until_required_goal_is_satisfied() -> None:
    store = InMemoryKnowledgeStore()
    dependency = make_goal(minimum_count=0)
    dependent = make_goal(
        minimum_count=0,
        dependencies=(GoalDependency(dependency.id),),
    )
    evaluator = InMemoryGoalEvaluator(store)
    assert evaluator.evaluate(dependent).status is GoalStatus.BLOCKED
    completed = evaluator.evaluate(dependency)
    assert evaluator.evaluate(
        dependent, dependency_evaluations=(completed,)
    ).status is GoalStatus.SATISFIED


def test_dependency_cycle_is_rejected() -> None:
    first_id, second_id = GoalId.new(), GoalId.new()
    first = Goal(
        first_id,
        "first",
        (),
        dependencies=(GoalDependency(second_id),),
        components=(second_id,),
    )
    second = Goal(
        second_id,
        "second",
        (),
        dependencies=(GoalDependency(first_id),),
        components=(first_id,),
    )
    with pytest.raises(ValueError, match="cycles"):
        InMemoryGoalEvaluator.validate_dependencies((first, second))


def test_goal_can_be_evaluated_against_snapshot() -> None:
    store = InMemoryVersionedKnowledgeStore()
    item = Entity(EntityId.new(), "concept", "Original")
    revision = store.save_revision(item)
    snapshot = store.create_snapshot()
    deleted = store.delete_revision(item.id, expected_revision_id=revision.revision_id)
    assert deleted.status is RevisionStatus.DELETED
    evaluator = InMemoryGoalEvaluator(store)
    assert evaluator.evaluate(make_goal()).status is GoalStatus.FAILED
    historical = evaluator.evaluate(make_goal(), snapshot_id=snapshot.snapshot_id)
    assert historical.status is GoalStatus.SATISFIED
    assert historical.snapshot_id == snapshot.snapshot_id


def test_self_dependency_and_duplicate_dependencies_are_rejected() -> None:
    goal_id = GoalId.new()
    with pytest.raises(ValueError):
        Goal(
            goal_id,
            "bad",
            (),
            dependencies=(GoalDependency(goal_id),),
            components=(GoalId.new(),),
        )
    dependency = GoalId.new()
    with pytest.raises(ValueError):
        Goal(
            GoalId.new(),
            "duplicates",
            (GoalCriterion(Query(), 0),),
            dependencies=(GoalDependency(dependency), GoalDependency(dependency)),
        )
