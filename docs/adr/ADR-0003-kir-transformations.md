# ADR-0003 — KIR Transformations

- Status: Accepted
- Date: 2026-07-24

## Decision

1. Structural transformations such as merge create a new identity, preserve source entities, and record explicit derivation links.
2. Relation propagation is governed by a declarative `RelationTransformationPolicy`; no affected relation is propagated implicitly.
3. KnowledgeUnit reformulation is represented by a first-class `KnowledgeUnitTransformation` with explicit semantic mappings between source and destination.
4. The semantic Core remains immutable; extensions operate only in formally declared extensible zones.

## Consequences

Transformations are auditable semantic objects rather than destructive edits. Relation outcomes must be classified explicitly, for example as preserved, copied, reformulated, omitted, not applicable, or requiring review.
