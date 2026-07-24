# ADR-0005 — Projections as versioned deterministic reducers

## Status

Accepted.

## Decision

Materialized views are produced by named, versioned projections. A projection is a pure reducer with an initial state, an event application function, and a finalization step. Rebuilds always consume events in stable stream order and persist both the projection version and the last processed sequence.

Projection state is disposable. The immutable event stream remains the source of truth, and any projection may be deleted and rebuilt without loss of knowledge.

## Consequences

- projection code cannot read connectors or mutate the event stream;
- identical ordered histories must yield identical finalized states;
- schema changes require a projection version change and rebuild;
- checkpoints describe materialization progress, not domain truth.
