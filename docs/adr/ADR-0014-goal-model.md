# ADR-0014 — Goal Model

## Status

Accepted.

## Context

The KIR needs a first-class, immutable representation of desired and verifiable
knowledge states without introducing planning or runtime behavior.

## Decision

Introduce `knowledge_architect.kir.goal` with immutable Goals, query-backed
criteria, constraints, dependencies, composition, priorities and deterministic
evaluations. `InMemoryGoalEvaluator` evaluates current or snapshot state and
never mutates knowledge. Dependency graphs are required to be acyclic.

## Consequences

Goals remain reusable and backend-independent. Planning and execution stay out
of scope and can consume evaluations in later RFCs.
