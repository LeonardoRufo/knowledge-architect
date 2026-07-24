from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from knowledge_architect.kir import (
    Entity,
    EntityId,
    Evidence,
    EvidenceId,
    EvidenceKind,
    ExtensionDefinition,
    ExtensionDefinitionValidator,
    ExtensionDependency,
    ExtensionId,
    ExtensionRegistry,
    KnowledgeUnit,
    KnowledgeUnitId,
    KnowledgeUnitKind,
    KnowledgeUnitTransformation,
    Provenance,
    ProvenanceId,
    ProvenanceKind,
    Relation,
    RelationEndpoint,
    RelationId,
    RelationTargetKind,
    RelationTransformationDecision,
    RelationTransformationOutcome,
    RelationTransformationPolicy,
    TransformationId,
    TransformationKind,
    TransformationMapping,
    ValidationCode,
    ValidationContext,
    ValidationError,
    ValidationIssue,
    ValidationMode,
    ValidationRegistry,
    ValidationResult,
    ValidationSeverity,
    core_validation_registry,
)


def _uuid(prefix: str, number: int) -> str:
    return f"{prefix}:123e4567-e89b-12d3-a456-{number:012d}"


def _provenance(number: int = 1) -> Provenance:
    return Provenance(
        ProvenanceId(_uuid("provenance", number)),
        ProvenanceKind.DERIVED,
        "knowledge-architect",
        datetime(2026, 7, 24, tzinfo=UTC),
    )


def test_validation_issue_is_normalized_and_immutable() -> None:
    issue = ValidationIssue(
        ValidationCode.MISSING_REFERENCE,
        ValidationSeverity.ERROR,
        " missing reference ",
        " unit:1 ",
    )
    assert issue.message == "missing reference"
    assert issue.location == "unit:1"
    with pytest.raises(FrozenInstanceError):
        issue.message = "changed"  # type: ignore[misc]


def test_validation_result_is_deterministically_sorted() -> None:
    warning = ValidationIssue(
        ValidationCode.MISSING_PROVENANCE,
        ValidationSeverity.WARNING,
        "warning",
        "b",
    )
    error_b = ValidationIssue(
        ValidationCode.MISSING_REFERENCE,
        ValidationSeverity.ERROR,
        "error b",
        "b",
    )
    error_a = ValidationIssue(
        ValidationCode.MISSING_REFERENCE,
        ValidationSeverity.ERROR,
        "error a",
        "a",
    )
    result = ValidationResult((warning, error_b, error_a))
    assert result.issues == (error_a, error_b, warning)


def test_validation_result_accumulates_and_raises() -> None:
    error = ValidationIssue(
        ValidationCode.INVALID_MAPPING,
        ValidationSeverity.ERROR,
        "invalid mapping",
    )
    warning = ValidationIssue(
        ValidationCode.MISSING_PROVENANCE,
        ValidationSeverity.WARNING,
        "missing provenance",
    )
    result = ValidationResult().add_issue(warning).extend((error,))
    assert not result.valid
    assert result.has_errors()
    assert result.errors == (error,)
    assert result.warnings == (warning,)
    with pytest.raises(ValidationError, match="1 error"):
        result.raise_if_invalid()


def test_registry_runs_all_matching_validators() -> None:
    class AlwaysWarn:
        def validate(self, obj: KnowledgeUnit, context: ValidationContext) -> ValidationResult:
            del obj, context
            return ValidationResult(
                (
                    ValidationIssue(
                        ValidationCode.MISSING_PROVENANCE,
                        ValidationSeverity.WARNING,
                        "warning",
                    ),
                )
            )

    registry = ValidationRegistry()
    registry.register(KnowledgeUnit, AlwaysWarn())
    unit = KnowledgeUnit(KnowledgeUnitId.new(), KnowledgeUnitKind.ASSERTION, "Content")
    assert len(registry.validate(unit).warnings) == 1
    with pytest.raises(ValueError, match="already registered"):
        validator = registry.validators_for(KnowledgeUnit)[0]
        registry.register(KnowledgeUnit, validator)


def test_registry_rejects_unknown_object_types() -> None:
    with pytest.raises(KeyError, match="no validators"):
        ValidationRegistry().validate(object())


def test_knowledge_unit_validator_accumulates_missing_references() -> None:
    unit = KnowledgeUnit(
        KnowledgeUnitId.new(),
        KnowledgeUnitKind.ASSERTION,
        "Content",
        (EntityId.new(),),
        (EvidenceId.new(),),
        ProvenanceId.new(),
    )
    result = core_validation_registry().validate(unit, ValidationContext())
    assert len(result.errors) == 3
    assert {issue.code for issue in result.errors} == {ValidationCode.MISSING_REFERENCE}


def test_missing_provenance_depends_on_validation_mode() -> None:
    unit = KnowledgeUnit(KnowledgeUnitId.new(), KnowledgeUnitKind.ASSERTION, "Content")
    registry = core_validation_registry()
    strict = registry.validate(unit, ValidationContext(mode=ValidationMode.STRICT))
    permissive = registry.validate(unit, ValidationContext(mode=ValidationMode.PERMISSIVE))
    assert len(strict.errors) == 1
    assert len(permissive.warnings) == 1
    assert permissive.valid


def test_valid_knowledge_unit_passes_with_complete_context() -> None:
    entity = Entity(EntityId.new(), "concept", "Validation")
    evidence = Evidence(EvidenceId.new(), EvidenceKind.OBSERVATION, "test", "1", "Observed")
    provenance = _provenance()
    unit = KnowledgeUnit(
        KnowledgeUnitId.new(),
        KnowledgeUnitKind.ASSERTION,
        "Validation is deterministic.",
        (entity.id,),
        (evidence.id,),
        provenance.id,
    )
    context = ValidationContext(
        entities={entity.id: entity},
        evidence={evidence.id: evidence},
        provenance={provenance.id: provenance},
    )
    assert core_validation_registry().validate(unit, context).valid


def test_relation_validator_reports_both_missing_endpoints() -> None:
    relation = Relation(
        RelationId.new(),
        "supports",
        RelationEndpoint(RelationTargetKind.ENTITY, EntityId.new()),
        RelationEndpoint(RelationTargetKind.KNOWLEDGE_UNIT, KnowledgeUnitId.new()),
    )
    result = core_validation_registry().validate(relation)
    assert len(result.errors) == 2


def test_transformation_validator_checks_context_references() -> None:
    source = KnowledgeUnitId.new()
    target = KnowledgeUnitId.new()
    transformation = KnowledgeUnitTransformation(
        TransformationId.new(),
        TransformationKind.REFORMULATION,
        (TransformationMapping((source,), (target,)),),
        ProvenanceId.new(),
    )
    result = core_validation_registry().validate(transformation)
    assert len(result.errors) == 2
    assert all(issue.code is ValidationCode.MISSING_REFERENCE for issue in result.errors)


def test_relation_requires_review_is_strict_or_permissive() -> None:
    source = KnowledgeUnit(KnowledgeUnitId.new(), KnowledgeUnitKind.ASSERTION, "Source")
    provenance = _provenance()
    transformation = KnowledgeUnitTransformation(
        TransformationId.new(),
        TransformationKind.NORMALIZATION,
        (TransformationMapping((source.id,), (KnowledgeUnitId.new(),)),),
        provenance.id,
        RelationTransformationPolicy(
            (
                RelationTransformationDecision(
                    RelationId.new(),
                    RelationTransformationOutcome.REQUIRES_REVIEW,
                ),
            )
        ),
    )
    base = {"knowledge_units": {source.id: source},"provenance": {provenance.id: provenance},}
    strict = core_validation_registry().validate(
        transformation, ValidationContext(mode=ValidationMode.STRICT, **base)
    )
    permissive = core_validation_registry().validate(
        transformation, ValidationContext(mode=ValidationMode.PERMISSIVE, **base)
    )
    assert strict.errors[0].code is ValidationCode.RELATION_REQUIRES_REVIEW
    assert permissive.warnings[0].code is ValidationCode.RELATION_REQUIRES_REVIEW


def test_extension_validator_reports_missing_dependency_without_mutating_registry() -> None:
    dependency = ExtensionDependency(ExtensionId.new(), "1.0.0")
    definition = ExtensionDefinition(
        ExtensionId.new(),
        "com.example.validation",
        "Validation extension",
        "1.0.0",
        dependencies=(dependency,),
    )
    registry = ExtensionRegistry()
    context = ValidationContext(extension_registry=registry)
    result = ExtensionDefinitionValidator().validate(definition, context)
    assert result.errors[0].code is ValidationCode.INVALID_EXTENSION
    assert registry.definitions() == ()


def test_extension_validator_accepts_registered_exact_dependency() -> None:
    dependency = ExtensionDefinition(
        ExtensionId.new(), "com.example.base", "Base", "1.0.0"
    )
    registry = ExtensionRegistry()
    registry.register(dependency)
    definition = ExtensionDefinition(
        ExtensionId.new(),
        "com.example.consumer",
        "Consumer",
        "1.0.0",
        dependencies=(ExtensionDependency(dependency.id, dependency.version),),
    )
    context = ValidationContext(extension_registry=registry)
    assert ExtensionDefinitionValidator().validate(definition, context).valid
