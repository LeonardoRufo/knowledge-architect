# RFC-009 — Storage-Independent Query Model

Status: Accepted

Author: Knowledge Architect Project

Created: 2026-07-24

## Summary

RFC-009 introduces the immutable, declarative query model of the Knowledge Intermediate
Representation. It separates query intent from execution and storage, supports predicate
composition, traversal declarations, ordering, pagination, projection, and deterministic
results, and defines a backend-neutral `QueryEngine` contract.

## Public API

`knowledge_architect.kir.query` exposes `Query`, `QueryResult`, `QueryEngine`, predicates,
combinators, traversals, `Ordering`, `Projection`, and `Pagination`. The KIR package root
re-exports these types.

## Constraints

Queries never modify state or execute themselves. Query engines may differ in algorithms
and physical mechanisms but may not alter query semantics. Persistence, indexing, cache,
optimization, textual syntax, parsers, and HTTP APIs are outside this RFC.

## Decision compatibility

The model preserves identity, relation-transformation policy, first-class transformations,
and the immutable Core boundary established by DEC-KIR-001, DEC-KIR-002, DEC-KIR-003,
and DEC-KIR-006.
