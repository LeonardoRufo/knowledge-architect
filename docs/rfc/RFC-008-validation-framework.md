# RFC-008: Formal KIR Validation Framework

## Status

Accepted

## Summary

Introduce a deterministic, composable validation framework for KIR objects. Validation reports accumulate typed issues instead of stopping at the first problem, while preserving the immutable Core's constructor-level invariants.

## Design

`ValidationIssue` carries a stable code, severity, message, and location. `ValidationResult` is immutable, deterministically ordered, and exposes errors, warnings, and informational issues. `ValidationContext` supplies known object registries, extension state, and strict or permissive policy without coupling domain objects to infrastructure.

`ValidationRegistry` dispatches one or more validators by object type. Core validators cover knowledge-unit references and provenance, relation endpoints, first-class transformations, transformation results, and extension dependencies.

Strict mode treats policy-sensitive omissions and review requirements as errors. Permissive mode downgrades only those policy-sensitive findings to warnings; structural Core violations and broken references remain errors.

## Invariants

- Validation never mutates the validated object or supplied registries.
- All discovered issues are accumulated.
- Result ordering is stable by severity, code, location, and message.
- Extensions may add validators but cannot replace or weaken Core validators.
- Constructor-level invariants remain authoritative for impossible object states.
