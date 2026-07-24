# ADR-0004 — Event identity and synchronization idempotency

## Status

Accepted.

## Decision

Knowledge events use separate occurrence and logical identities:

- `event_id` is a UUID generated for each event occurrence;
- `content_fingerprint` identifies normalized source content;
- `idempotency_key` deterministically identifies the logical observation.

Persistence deduplicates by `idempotency_key` when one is present, not by making
`event_id` deterministic.

## Rationale

A deterministic event identifier would collapse occurrence identity into
logical identity. Keeping them separate permits auditability while preventing
repeated source reads from polluting the event stream.

## Consequences

Event producers that require idempotency must provide a stable key. Producers
for which deduplication is not meaningful may leave the key unset.
