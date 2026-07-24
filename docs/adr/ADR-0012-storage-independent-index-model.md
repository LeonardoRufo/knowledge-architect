# ADR-0012 — Storage-Independent Index Model

**Status:** Accepted  
**Date:** 2026-07-24

## Context

RFC-009 established backend-neutral query semantics and RFC-010 established the
`KnowledgeStore` persistence Port. Full scans remain correct but need a formal,
disposable acceleration mechanism that cannot become a second source of truth.

## Decision

Introduce `knowledge_architect.kir.index` with:

- `SearchIndex`, the storage-independent derived-index contract;
- `IndexManager`, which rebuilds and updates indexes from a `KnowledgeStore`;
- immutable `IndexCapabilities`, `IndexResult`, and `IndexStatistics` values;
- `InMemorySearchIndex`, providing hash-based identity, kind, and namespace
  lookup without external dependencies.

The Store remains authoritative. An index may return only candidate identities.
The Store always retrieves entities and applies the complete RFC-009 query
semantics. Unsupported predicates, traversals, missing indexes, and invalid
indexes transparently use a full scan.

Store mutations notify an attached `IndexManager`. An update failure invalidates
the affected index instead of changing the persisted operation or query
semantics. Every index can be completely rebuilt from `KnowledgeStore.list()`.

## Consequences

- Indexed and non-indexed execution have identical observable results.
- Indexes are safe to discard, invalidate, or rebuild.
- Index backends remain independent from persistence backends.
- Additional index types can extend the Port without modifying the KIR Core.
- Query optimization remains conservative: only predicates proven safe are used
  for candidate reduction.
