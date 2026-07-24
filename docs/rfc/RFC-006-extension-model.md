# RFC-006 — Formal KIR Extension Model

## Status

Implemented.

## Motivation

RFC-005 establishes an immutable semantic Core. The system still needs a formal way to add domain-specific types, constraints, projections, transformations, and serializers without allowing extensions to redefine Core identity, semantics, or invariants.

## Design

The package `knowledge_architect.kir` now defines:

- `ExtensionId`, a typed immutable identity;
- `ExtensionCapability`, a namespaced capability declaration;
- `ExtensionCapabilityKind`, covering types, constraints, projections, transformations, and serializers;
- `ExtensionDependency`, an exact dependency on an extension identity and semantic version;
- `ExtensionDefinition`, an immutable extension manifest;
- `ExtensionRegistry`, which validates identity, namespace, version, and dependency consistency.

Extension namespaces use lowercase reverse-domain-style identifiers. Capability names are local identifiers and are qualified by their owning extension namespace. Reserved Core roots cannot be used by extensions.

## Invariants

1. Extension definitions and declarations are immutable.
2. Every extension has a typed identity, namespace, and semantic version.
3. An extension may only declare capabilities in its own namespace.
4. Core namespace roots are reserved and cannot be claimed by extensions.
5. Capabilities are unique by kind and local name within an extension.
6. Dependencies are explicit, unique, non-circular at the direct self-reference level, and version-exact.
7. A registry rejects duplicate identities, duplicate namespaces, missing dependencies, and version mismatches.
8. Extension serialization remains canonical and deterministic.

## Non-goals

RFC-006 does not:

- execute extension code;
- dynamically import plugins;
- persist registry state;
- introduce structural merge or reformulation operations;
- permit extensions to replace or alter Core object definitions.

Execution and transformation semantics remain subjects of later RFCs.
