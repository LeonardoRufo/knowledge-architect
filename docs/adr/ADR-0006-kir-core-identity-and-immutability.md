# ADR-0006 — Typed identity and immutable KIR Core

## Status

Accepted.

## Decision

The KIR Core is represented by immutable, typed domain objects. Each object category has a distinct identity type whose serialized form contains a category prefix and UUID. Core objects are frozen dataclasses and validate their invariants at construction time.

The Core is a semantic boundary rather than a persistence schema. It must not depend on connectors, databases, application handlers, or materialized projections. Serialization is canonical and deterministic, but storage remains outside this decision.

## Consequences

- accidental cross-type identity use is rejected early;
- transformations cannot mutate existing Core objects and must produce new identities;
- extensions cannot redefine Core object meaning or invariants;
- object construction may fail when semantic inputs are incomplete or invalid;
- adapters must translate external representations into valid Core objects explicitly.
