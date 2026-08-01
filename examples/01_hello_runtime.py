from knowledge_architect.kir import (
    GoalId,
    Plan,
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
    return StepOutcome(result=f"{step.name} concluída")


def main() -> None:
    collect = PlanStep(
        id=PlanStepId.new(),
        name="Collect",
        description="Collect knowledge",
    )

    validate = PlanStep(
        id=PlanStepId.new(),
        name="Validate",
        description="Validate knowledge",
    )

    plan = Plan(
        id=PlanId.new(),
        name="Hello Runtime",
        description="Primeiro exemplo do runtime",
        goal_ids=(GoalId.new(),),
        graph=PlanGraph((collect, validate)),
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

    print("\n========== EVENTOS ==========")

    history = runtime.history(result.execution_id)

    for event in history.events:
        print(
            f"{event.sequence:02d}",
            event.event_type,
            event.state.value,
        )

    print("\n✅ Runtime executado com sucesso.")


if __name__ == "__main__":
    main()