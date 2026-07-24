# RFC-010 — Persistent Knowledge Store

**Status:** Accepted

**Created:** 2026-07-24

RFC-010 introduces `KnowledgeStore` as the backend-independent persistence Port for KIR
objects. The public contract includes save, bulk save, load, existence checks, delete,
deterministic listing and counting, RFC-009 query execution, clear, and logical
transactions. Conflict behavior is explicit through `StoreConflictPolicy`.

The initial `InMemoryKnowledgeStore` reference adapter introduces no external dependency
or database. It preserves the original immutable objects and their canonical
serialization, supports deterministic query evaluation and graph traversal, and provides
atomic logical transactions through snapshot rollback.

Indexing, search optimization, database adapters, cache, replication, and distributed
versioning are intentionally deferred.
