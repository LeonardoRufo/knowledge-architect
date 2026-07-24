# RFC-001 — Application Layer

- Status: Implemented (first increment)
- Date: 2026-07-24

## Goal

Move synchronization orchestration out of the CLI while preserving observable behavior.

## Implemented scope

- `SyncSourceArtifactCommand`
- `SyncSourceArtifactHandler`
- `SyncSourceArtifactResult`
- CLI delegation to the handler
- isolated handler test

## Deliberately deferred

The handler still depends on concrete `NotionConnector` and `SQLiteEventStore` types. RFC-002 will introduce source-provider and event-store ports. RFC-003 will separate event creation from the connector and implement observation idempotency.
