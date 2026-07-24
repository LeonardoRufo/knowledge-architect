# RFC-012 — Knowledge Versioning and Store Snapshots

Status: Proposed

The implementation introduces immutable entity revisions, linear history,
optimistic concurrency, tombstones, restoration, deterministic store snapshots,
and the `VersionedKnowledgeStore` Port. The in-memory reference adapter keeps
only current active entities in the RFC-010 store and RFC-011 indexes while
retaining all revisions and snapshot references as historical truth.
