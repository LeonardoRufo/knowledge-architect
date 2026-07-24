# ADR-0007 — Namespaced extensions over an immutable KIR Core

## Status

Accepted.

## Decision

KIR extensions are immutable, explicitly versioned manifests whose capabilities exist only in extension-owned namespaces. The KIR Core namespace and its semantic invariants are reserved and cannot be claimed, replaced, weakened, or reinterpreted by an extension.

Dependencies between extensions are explicit and version-exact at registration time. Registration validates identity and namespace uniqueness before an extension becomes available.

## Consequences

- domain-specific capabilities can evolve without changing Core identities or semantics;
- namespace ownership prevents accidental or hostile Core redefinition;
- extension dependency resolution is deterministic;
- registration order follows dependency order;
- incompatible dependency versions fail early;
- runtime plugin loading and code execution remain separate concerns.
