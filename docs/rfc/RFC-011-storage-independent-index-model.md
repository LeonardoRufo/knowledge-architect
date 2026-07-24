# RFC-011 — Storage-Independent Index Model

**Status:** Accepted  
**Created:** 2026-07-24

This RFC introduces disposable, storage-independent indexes for accelerating
RFC-009 queries over RFC-010 stores. `KnowledgeStore` remains the only source of
truth, and query behavior is identical with or without indexes.

The public API is provided by `knowledge_architect.kir.index`:

- `SearchIndex`
- `IndexManager`
- `IndexCapabilities`
- `IndexResult`
- `IndexStatistics`
- `InMemorySearchIndex`

The reference index provides hash-based lookup by identity, entity kind, and
namespace. Unsupported or invalid index paths fall back to full Store scans.
All derived state can be rebuilt solely from the Store.
