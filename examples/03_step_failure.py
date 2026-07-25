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


def step_handler(step: PlanStep, context: RuntimeContext) -> StepOutcome:
    print(f"▶ Executando: {step.name}")

    if step.name == "Validate":
        raise RuntimeError("Falha simulada durante a validação")

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
        name="Step Failure",
        description="Example of a failed plan step",
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

    runtime = InMemoryRuntime(step_handler=step_handler)

    result = runtime.execute(
        revision,
        RuntimeContext(),
    )

    print("\n========== RESULTADO ==========")
    print("Estado:", result.state)

    print("\n========== EVENTOS ==========")

    history = runtime.history(result.execution_id)

    for event in history.events:
        print(
            f"{event.sequence:02d}",
            event.event_type,
            event.state.value,
        )

    assert result.state == ExecutionState.FAILED

    print("\n✅ Falha registrada corretamente.")


if __name__ == "__main__":
    main()