# ADR-0002 — Event Sourcing

- Status: Accepted
- Date: 2026-07-24

## Context

The system must preserve observations and decisions as an auditable history while supporting rebuildable current-state views.

## Decision

The Event Store is the authoritative history. Projections are derived and rebuildable. Events are append-only occurrences with unique `event_id` values.

Idempotency is conceptually separate from occurrence identity. A future event schema will introduce a deterministic `idempotency_key` and content fingerprint; deduplication must not depend on deterministic event IDs.

## Consequences

- Materialized state can be deleted and rebuilt.
- Historical events are not mutated.
- Event schema evolution requires explicit versioning.
- Synchronizing an unchanged observation will eventually produce no new domain event.
