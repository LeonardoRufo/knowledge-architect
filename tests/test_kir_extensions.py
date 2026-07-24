from dataclasses import FrozenInstanceError

import pytest

from knowledge_architect.kir import (
    ExtensionCapability,
    ExtensionCapabilityKind,
    ExtensionDefinition,
    ExtensionDependency,
    ExtensionId,
    ExtensionRegistry,
    canonical_json,
)


def _definition(
    *,
    extension_id: ExtensionId | None = None,
    namespace: str = "org.example.medical",
    version: str = "1.0.0",
    dependencies: tuple[ExtensionDependency, ...] = (),
) -> ExtensionDefinition:
    return ExtensionDefinition(
        id=extension_id or ExtensionId.new(),
        namespace=namespace,
        name="Medical knowledge extension",
        version=version,
        capabilities=(
            ExtensionCapability(
                name="clinical_finding",
                kind=ExtensionCapabilityKind.TYPE,
                description="Adds a clinical finding type.",
            ),
            ExtensionCapability(
                name="validated_evidence",
                kind=ExtensionCapabilityKind.CONSTRAINT,
            ),
        ),
        dependencies=dependencies,
    )


def test_extension_definition_is_immutable_and_namespaces_capabilities() -> None:
    definition = _definition()

    assert definition.capability_names == (
        "org.example.medical.clinical_finding",
        "org.example.medical.validated_evidence",
    )

    with pytest.raises(FrozenInstanceError):
        definition.version = "2.0.0"  # type: ignore[misc]


def test_extension_rejects_reserved_or_invalid_namespaces() -> None:
    with pytest.raises(ValueError, match="reserved"):
        _definition(namespace="kir.core")

    with pytest.raises(ValueError, match="reverse-domain"):
        _definition(namespace="Medical")


def test_extension_rejects_invalid_version_and_duplicate_capabilities() -> None:
    with pytest.raises(ValueError, match="semantic version"):
        _definition(version="1.0")

    capability = ExtensionCapability("finding", ExtensionCapabilityKind.TYPE)
    with pytest.raises(ValueError, match="capabilities"):
        ExtensionDefinition(
            id=ExtensionId.new(),
            namespace="org.example.duplicate",
            name="Duplicate",
            version="1.0.0",
            capabilities=(capability, capability),
        )


def test_registry_validates_dependencies_and_namespace_uniqueness() -> None:
    registry = ExtensionRegistry()
    base = _definition(namespace="org.example.base")
    registry.register(base)

    dependent = _definition(
        namespace="org.example.dependent",
        dependencies=(ExtensionDependency(base.id, "1.0.0"),),
    )
    registry.register(dependent)

    assert registry.get(base.id) is base
    assert registry.get_by_namespace(dependent.namespace) is dependent
    assert registry.definitions() == (base, dependent)

    with pytest.raises(ValueError, match="namespace already"):
        registry.register(_definition(namespace=base.namespace))


def test_registry_rejects_missing_or_wrong_dependency_version() -> None:
    missing_id = ExtensionId.new()
    registry = ExtensionRegistry()

    with pytest.raises(ValueError, match="missing extension dependency"):
        registry.register(
            _definition(
                dependencies=(ExtensionDependency(missing_id, "1.0.0"),),
            )
        )

    base = _definition(namespace="org.example.base")
    registry.register(base)
    with pytest.raises(ValueError, match="version mismatch"):
        registry.register(
            _definition(
                namespace="org.example.consumer",
                dependencies=(ExtensionDependency(base.id, "2.0.0"),),
            )
        )


def test_extension_serialization_is_deterministic() -> None:
    definition = ExtensionDefinition(
        id=ExtensionId("extension:123e4567-e89b-12d3-a456-426614174000"),
        namespace="org.example.medical",
        name="Medical",
        version="1.2.3",
        capabilities=(
            ExtensionCapability("finding", ExtensionCapabilityKind.TYPE),
        ),
    )

    assert canonical_json(definition) == (
        '{"capabilities":[{"description":"","kind":"type","name":"finding"}],'
        '"dependencies":[],"description":"",'
        '"id":"extension:123e4567-e89b-12d3-a456-426614174000",'
        '"name":"Medical","namespace":"org.example.medical","version":"1.2.3"}'
    )
