# ADR-0001 — Core Architecture

- Status: Accepted
- Date: 2026-07-24

## Context

Knowledge Architect must evolve from an executable prototype into a durable system without coupling interfaces, external sources, semantic representation, and infrastructure.

## Decision

Adopt directional layers:

```text
Interfaces → Application → Domain → Ports → Adapters
```

Dependencies must point inward. Interfaces translate user input. Application handlers orchestrate use cases. Domain objects define semantics. Ports express required capabilities. Adapters integrate external systems and persistence.

The KIR semantic Core is immutable. Extensions may add capabilities in their own namespaces, but cannot redefine Core identity, semantics, or invariants.

## Consequences

- CLI commands must not contain domain workflows.
- Connectors must not define KIR semantics.
- Infrastructure must be replaceable behind ports.
- Refactoring will be incremental and behavior-preserving.
