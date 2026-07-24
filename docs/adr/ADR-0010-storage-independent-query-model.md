# ADR-0010: Use a storage-independent declarative KIR query model

## Status

Accepted

## Context

The immutable KIR Core can represent and validate knowledge, but querying it through
storage-specific APIs would couple semantic intent to infrastructure. Memory, SQL,
graph, RDF, and future engines must share the same query semantics.

## Decision

Introduce immutable `Query`, predicate, traversal, ordering, projection, and pagination
value objects in `knowledge_architect.kir.query`. A backend-neutral `QueryEngine`
executes query intent and returns an immutable `QueryResult`. Query construction never
performs execution and no query component imports persistence or adapter code.

## Consequences

Queries are canonically serializable, composable, deterministic, and portable across
execution engines. Backends may choose algorithms and physical plans, but cannot change
the meaning of existing predicates, traversals, ordering, projection, or pagination.
Persistence, indexing, textual syntax, parsing, and optimization remain deferred.
