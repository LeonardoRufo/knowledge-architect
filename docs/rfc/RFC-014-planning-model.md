# RFC-014 — Planning Model

Status: Proposed

RFC-014 introduces immutable Plans as declarative strategies for satisfying Goals. A Plan
contains first-class steps arranged as a validated DAG, Query-backed preconditions,
postconditions and completion criteria, optional subplans, expected transformations, and
canonical metadata. Plans contain no execution state.

The reference implementation provides `PlanValidator` and a version-aware
`InMemoryPlanRepository` without external dependencies.
