# RFC-003 — Observation and Idempotency

## Status

Implemented.

## Context

Before this RFC, every synchronization generated a fresh `event_id`. Because the
SQLite store deduplicated only by that occurrence identifier, fetching an
unchanged source repeatedly created duplicate logical facts.

## Decision

Source synchronization now distinguishes three identities:

- `event_id`: random UUID identifying one concrete event occurrence;
- `content_fingerprint`: SHA-256 of normalized source content;
- `idempotency_key`: deterministic SHA-256 of event type, source identity, and
  content fingerprint.

`SourceObservation` represents the point-in-time observation before it is
translated into `KnowledgeEvent`. `SourceObservationEventFactory` owns this
translation; source connectors remain responsible only for acquisition and
normalization.

The SQLite event store enforces a partial unique index on non-null
`idempotency_key` values. Existing databases are migrated in place by adding the
new nullable columns, preserving compatibility with historical events.

## Consequences

- repeated synchronization of unchanged content inserts no new event;
- changed content creates a new event and remains fully replayable;
- occurrence identity is preserved even when a duplicate is rejected;
- old events without an idempotency key remain readable;
- normalization policy becomes part of the observable event semantics and must
  evolve deliberately.
