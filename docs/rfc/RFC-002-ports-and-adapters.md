# RFC-002 — Application Ports

- **Status:** Implemented
- **Scope:** Application dependency boundaries

## Context

RFC-001 moved synchronization orchestration out of the CLI, but the handler still
imported the concrete Notion connector and SQLite event store. This coupled the
application use case to infrastructure choices.

## Decision

Introduce structural `Protocol` ports for:

- `SourceProviderPort`: fetches a normalized `SourceDocument`;
- `EventFactoryPort`: converts a document into a `KnowledgeEvent`;
- `EventStorePort`: appends, lists, and counts events.

`SyncSourceArtifactHandler` depends exclusively on these ports. The CLI is the
composition root and injects the current Notion and SQLite implementations.

## Consequences

- The synchronization use case can be tested without Notion or SQLite-specific
  imports.
- New source providers and event-store adapters can be added without changing
  the handler.
- Event construction is explicitly separated from source acquisition, preparing
  RFC-003 to introduce observations, fingerprints, and idempotency.
- Physical relocation of legacy adapters is deferred to avoid unnecessary import
  churn in this behavior-preserving RFC.
