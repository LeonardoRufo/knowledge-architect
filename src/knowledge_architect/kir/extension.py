from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType

from .identity import ExtensionId

_NAMESPACE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:\.[a-z][a-z0-9_-]*)+$")
_CAPABILITY_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*$")
_VERSION_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
_RESERVED_NAMESPACE_ROOTS = frozenset({"core", "kir", "knowledge_architect"})


def _validate_version(value: str, field_name: str = "version") -> None:
    if not _VERSION_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} must use semantic version form MAJOR.MINOR.PATCH")


class ExtensionCapabilityKind(StrEnum):
    TYPE = "type"
    CONSTRAINT = "constraint"
    PROJECTION = "projection"
    TRANSFORMATION = "transformation"
    SERIALIZER = "serializer"


@dataclass(frozen=True, slots=True)
class ExtensionCapability:
    """A capability added by an extension inside its own namespace."""

    name: str
    kind: ExtensionCapabilityKind
    description: str = ""

    def __post_init__(self) -> None:
        normalized_name = self.name.strip()
        if not _CAPABILITY_NAME_PATTERN.fullmatch(normalized_name):
            raise ValueError("capability name must be a lowercase dotted identifier")
        normalized_description = self.description.strip()
        object.__setattr__(self, "name", normalized_name)
        object.__setattr__(self, "description", normalized_description)

    def qualified_name(self, namespace: str) -> str:
        return f"{namespace}.{self.name}"


@dataclass(frozen=True, slots=True)
class ExtensionDependency:
    """Exact dependency on another registered extension version."""

    extension_id: ExtensionId
    version: str

    def __post_init__(self) -> None:
        _validate_version(self.version, "dependency version")


@dataclass(frozen=True, slots=True)
class ExtensionDefinition:
    """Immutable declaration of namespaced KIR extension capabilities."""

    id: ExtensionId
    namespace: str
    name: str
    version: str
    capabilities: tuple[ExtensionCapability, ...] = field(default_factory=tuple)
    dependencies: tuple[ExtensionDependency, ...] = field(default_factory=tuple)
    description: str = ""

    def __post_init__(self) -> None:
        namespace = self.namespace.strip()
        if not _NAMESPACE_PATTERN.fullmatch(namespace):
            raise ValueError("namespace must be a lowercase reverse-domain-style identifier")
        if namespace.split(".", maxsplit=1)[0] in _RESERVED_NAMESPACE_ROOTS:
            raise ValueError("namespace root is reserved by the immutable KIR Core")

        name = self.name.strip()
        if not name:
            raise ValueError("name must not be empty")
        _validate_version(self.version)

        capability_keys = tuple((capability.kind, capability.name) for capability in self.capabilities)
        if len(set(capability_keys)) != len(capability_keys):
            raise ValueError("capabilities must be unique by kind and name")

        dependency_ids = tuple(dependency.extension_id for dependency in self.dependencies)
        if self.id in dependency_ids:
            raise ValueError("extension cannot depend on itself")
        if len(set(dependency_ids)) != len(dependency_ids):
            raise ValueError("dependencies must be unique by extension_id")

        object.__setattr__(self, "namespace", namespace)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "description", self.description.strip())

    @property
    def capability_names(self) -> tuple[str, ...]:
        return tuple(capability.qualified_name(self.namespace) for capability in self.capabilities)


class ExtensionRegistry:
    """Registry enforcing identity, namespace, version, and dependency invariants."""

    def __init__(self) -> None:
        self._by_id: dict[ExtensionId, ExtensionDefinition] = {}
        self._by_namespace: dict[str, ExtensionDefinition] = {}

    def register(self, definition: ExtensionDefinition) -> None:
        if definition.id in self._by_id:
            raise ValueError(f"extension id already registered: {definition.id}")
        if definition.namespace in self._by_namespace:
            raise ValueError(f"extension namespace already registered: {definition.namespace}")

        for dependency in definition.dependencies:
            registered = self._by_id.get(dependency.extension_id)
            if registered is None:
                raise ValueError(f"missing extension dependency: {dependency.extension_id}")
            if registered.version != dependency.version:
                raise ValueError(
                    "extension dependency version mismatch: "
                    f"expected {dependency.version}, found {registered.version}"
                )

        self._by_id[definition.id] = definition
        self._by_namespace[definition.namespace] = definition

    def get(self, extension_id: ExtensionId) -> ExtensionDefinition:
        try:
            return self._by_id[extension_id]
        except KeyError as exc:
            raise KeyError(f"unknown extension id: {extension_id}") from exc

    def get_by_namespace(self, namespace: str) -> ExtensionDefinition:
        try:
            return self._by_namespace[namespace]
        except KeyError as exc:
            raise KeyError(f"unknown extension namespace: {namespace}") from exc

    def definitions(self) -> tuple[ExtensionDefinition, ...]:
        return tuple(sorted(self._by_id.values(), key=lambda item: (item.namespace, item.version)))

    @property
    def by_id(self) -> Mapping[ExtensionId, ExtensionDefinition]:
        return MappingProxyType(self._by_id)
