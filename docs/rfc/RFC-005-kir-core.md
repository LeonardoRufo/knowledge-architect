# RFC-005 — Immutable KIR Core

## Status

Implemented.

## Motivation

RFCs 001–004 establish acquisition, event storage, and projection infrastructure. They do not yet define a canonical semantic representation. RFC-005 introduces the smallest stable KIR Core needed to represent semantic objects independently from connectors, persistence, and query projections.

## Design

The package `knowledge_architect.kir` defines:

- typed immutable identities for every Core object;
- `Entity`, a stable referent;
- `KnowledgeUnit`, an atomic semantic statement;
- `Relation`, an explicit directed connection;
- `Evidence`, support anchored in a source or observation;
- `Provenance`, origin metadata;
- deterministic conversion to primitives and canonical JSON.

All Core objects use frozen slotted dataclasses. Domain validation occurs at construction time. The package has no dependency on SQLite, connectors, application handlers, or projection code.

## Invariants

1. Every Core object has a typed identity.
2. Identities are immutable and cannot be reused across Core object types.
3. Core objects are immutable after construction.
4. Empty semantic content and invalid cross-type references are rejected.
5. Relations are explicit; no relation is inferred or propagated by the Core.
6. Serialization of the same object is deterministic.
7. Structural transformations are outside this RFC and must create new identities.
8. Extensions may add future capabilities but cannot redefine Core semantics or invariants.

## Non-goals

RFC-005 does not introduce:

- persistence for KIR objects;
- projection integration;
- CLI commands;
- extension registries;
- merge or reformulation operations;
- lineage traversal.

Those capabilities are reserved for later RFCs.
