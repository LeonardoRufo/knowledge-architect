# ADR-0013 — Knowledge Versioning and Store Snapshots

## Status

Accepted — 2026-07-24

## Context

The KIR Store preserves only current state. Auditability, optimistic concurrency,
logical deletion, and reproducible global states require an explicit historical
layer without changing Core identity or query semantics.

## Decision

Add `knowledge_architect.kir.versioning` as an optional persistence capability.
`EntityId` remains the stable logical identity. Immutable `EntityRevision`
objects form one linear history per entity and receive unique `RevisionId`
values. Updates require the expected current revision. Deletion creates a
`tombstone`; restoration creates a later active revision.

Immutable `KnowledgeSnapshot` objects capture deterministic references to exact
revisions. The `KnowledgeStore` remains authoritative, while indexes represent
only current active entities and remain discardable derived data.

## Consequences

Existing `KnowledgeStore` consumers remain compatible. Version-aware backends
may implement `VersionedKnowledgeStore`. Historical storage and transactional
complexity increase, but stale writes become explicit and previous states are
reproducible without redefining Core semantics.
