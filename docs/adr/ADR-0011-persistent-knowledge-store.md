# ADR-0011 — Persistent Knowledge Store Port

**Status:** Accepted

**Date:** 2026-07-24

## Context

The immutable KIR Core and the storage-independent Query Model require a persistence
boundary that does not introduce database concepts into domain objects or queries.

## Decision

Introduce `knowledge_architect.kir.store` with a single `KnowledgeStore` Port. The Port
preserves typed identity and canonical KIR serialization while exposing explicit conflict
policies. `StoreTransaction`, `StoreResult`, store-specific errors, and declared
`StoreCapabilities` form part of the contract.

`InMemoryKnowledgeStore` is the reference adapter. It stores the original immutable KIR
objects by typed identity, validates canonical serialization before persistence, lists
objects in deterministic identity order, and executes RFC-009 queries without modifying
them. Its transaction implementation stages operations and restores a complete snapshot
when commit fails.

## Consequences

- The KIR Core has no dependency on SQLite, SQL, files, or external packages.
- Adapters may use different physical storage while preserving the same Port semantics.
- Identity conflicts are never implicit: callers choose reject, replace, or update.
- Canonical serialization is validated at the persistence boundary.
- Indexing, optimization, external databases, and distributed versioning remain outside
  this decision.
