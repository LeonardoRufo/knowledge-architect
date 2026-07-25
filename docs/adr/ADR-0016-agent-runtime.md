# ADR-0016 — Agent Runtime

## Status

Accepted — 2026-07-24

## Decision

Introduce `knowledge_architect.runtime` as a package outside KIR. The runtime consumes an immutable `PlanRevision`, creates an independently identified execution, and records every state change as an append-only immutable event.

The reference `InMemoryRuntime` is synchronous, deterministic when supplied deterministic collaborators, thread-safe, and reconstructs execution state exclusively from its event history. Query-backed preconditions, postconditions, and completion criteria are evaluated through the existing `QueryEngine` port. Step behavior is injected through a small handler contract; tool execution remains outside this RFC.

## Consequences

Plans and Goals remain immutable. Runtime state is not stored in KIR entities. Execution persistence can later replace the in-memory event collection without changing the declarative model or event-reconstruction semantics.
