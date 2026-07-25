# ADR-0015 — Planning Model

## Status

Accepted — 2026-07-24

## Decision

Represent strategies as immutable `Plan` objects composed of first-class `PlanStep`
objects in a directed acyclic graph. Plans reference the Goals they intend to satisfy,
but contain no execution state, scheduling, tools, or runtime behavior.

Conditions and completion criteria reuse the storage-independent `Query` model. Structural
validation rejects unknown dependencies, cycles, duplicate identities, and recursive
subplan graphs. `InMemoryPlanRepository` is the reference adapter and preserves immutable,
linear plan revisions through optimistic concurrency.

## Consequences

Goal, Plan, and future Runtime remain separate. Multiple plans may target one Goal, plans
are reusable, and future executors can interpret the DAG without changing its semantics.
