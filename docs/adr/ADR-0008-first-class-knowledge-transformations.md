# ADR-0008 — First-class knowledge transformations

## Status

Accepted.

## Decision

Represent KnowledgeUnit transformations as immutable first-class KIR objects. Every structural or semantic transformation creates new target identities, preserves source identities, records explicit source-to-target mappings and provenance, and declares relation handling through a formal policy.

## Rationale

A mutable replacement model destroys auditability. A simple predecessor reference cannot express merge, split, or many-to-many semantic correspondence. Automatic relation propagation can silently preserve invalid semantics. First-class transformations make derivation and uncertainty explicit.

## Consequences

Transformation producers must create new IDs and complete records. Relation effects are never inferred by the Core. Execution engines may be added later, but they must emit records conforming to these invariants.
