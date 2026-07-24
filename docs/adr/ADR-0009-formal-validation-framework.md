# ADR-0009: Use a formal, accumulative KIR validation framework

## Status

Accepted

## Context

Cross-object integrity cannot be enforced by immutable value-object constructors alone. References, extension dependencies, and transformation review decisions require external context and complete diagnostics.

## Decision

Use immutable validation issues and results, contextual validators, and a type-based registry. Core validation accumulates findings deterministically. Strict and permissive modes may change only policy-sensitive severity; neither mode may weaken structural Core invariants.

## Consequences

Consumers receive complete, machine-readable diagnostics. Future import, query, extension, and AI workflows share one validation contract. Core objects remain free of application and adapter dependencies.
