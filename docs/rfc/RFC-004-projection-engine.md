# RFC-004 — Projection Engine

## Status

Implemented.

## Motivation

The event stream records immutable observations but is not an efficient query model. The existing function-based materializer also has no explicit identity, version, checkpoint, or persistent snapshot contract.

## Design

RFC-004 introduces:

- `StoredEvent`, pairing an event with its stable stream sequence;
- `EventStorePort.list_stream(after_sequence=...)`;
- `ProjectionPort`, a deterministic reducer contract;
- `ProjectionRegistry` for named projection discovery;
- `ProjectionStorePort` and `SQLiteProjectionStore`;
- `SourceDocumentProjection` version 1;
- `RebuildProjectionHandler`;
- CLI commands `kaa projection rebuild` and `kaa projection show`.

A complete rebuild follows this pipeline:

```text
ordered event stream
        ↓
projection.initial_state()
        ↓
projection.apply(state, event)
        ↓
projection.finalize(state)
        ↓
versioned snapshot + last_sequence
```

## Invariants

1. The event stream is the only source of truth.
2. Rebuilding from the same ordered stream produces the same finalized state.
3. Projection snapshots are replaceable and disposable.
4. Projection versions are explicit.
5. Checkpoints use persisted stream sequence numbers, never timestamps.

## Compatibility

The original `materialize()` function remains available during migration. RFC-004 adds the projection engine without silently changing existing status or export behavior.
