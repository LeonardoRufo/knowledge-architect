from knowledge_architect.kir import (
    GoalId,
    Plan,
    PlanDependency,
    PlanGraph,
    PlanId,
    PlanRevision,
    PlanStep,
    PlanStepId,
    RevisionId,
)
from knowledge_architect.runtime import (
    ExecutionState,
    InMemoryRuntime,
    RuntimeContext,
    StepOutcome,
)

execution_order: list[str] = []


def step_handler(step: PlanStep, context: RuntimeContext) -> StepOutcome:
    execution_order.append(step.name)
    print(f"▶ Executando: {step.name}")
    return StepOutcome(result=f"{step.name} concluída")


def main() -> None:
    collect_id = PlanStepId.new()
    validate_id = PlanStepId.new()

    collect = PlanStep(
        id=collect_id,
        name="Collect",
        description="Collect knowledge",
    )

    validate = PlanStep(
        id=validate_id,
        name="Validate",
        description="Validate knowledge",
        dependencies=(
            PlanDependency(step_id=collect_id),
        ),
    )

    plan = Plan(
        id=PlanId.new(),
        name="Plan Dependencies",
        description="Example with explicit step dependencies",
        goal_ids=(GoalId.new(),),
        graph=PlanGraph(
            steps=(
                validate,
                collect,
            )
        ),
    )

    revision = PlanRevision(
        revision_id=RevisionId.new(),
        plan=plan,
        revision_number=1,
    )

    runtime = InMemoryRuntime(
        step_handler=step_handler,
    )

    result = runtime.execute(
        revision,
        RuntimeContext(),
    )

    print("\n========== RESULTADO ==========")
    print("Estado:", result.state)

    assert result.state == ExecutionState.SUCCEEDED
    assert execution_order == ["Collect", "Validate"]

    print("\nOrdem executada:", " → ".join(execution_order))
    print("\n✅ Dependência respeitada com sucesso.")


if __name__ == "__main__":
    main()