# RFC-007 — Knowledge Transformations

## Status

Accepted.

## Context

The immutable KIR Core represents semantic objects, but it must also represent how new knowledge is derived without mutating or erasing its sources. Merge, split, reformulation, summarization, translation, normalization, and extraction all require auditable identity and provenance semantics.

## Decision

Introduce immutable first-class `KnowledgeUnitTransformation` records with:

- a typed `TransformationId`;
- an explicit transformation kind;
- semantic mappings from source units to newly identified target units;
- mandatory derivation provenance;
- a declarative `RelationTransformationPolicy`;
- a validated `TransformationResult` binding the record to created objects.

Source and target identities must be disjoint. Merge and split shapes are validated. Every affected relation represented in a policy receives exactly one explicit classification: `preserved`, `copied`, `reformulated`, `omitted`, `not_applicable`, or `requires_review`. No implicit propagation occurs.

## Consequences

Transformations become part of the auditable semantic graph. Source objects remain unchanged and addressable. Consumers can reconstruct derivation paths, inspect relation-handling decisions, and reject incomplete or inconsistent transformation results.

This RFC does not execute transformation algorithms. It defines the canonical records and invariants those algorithms must produce.
