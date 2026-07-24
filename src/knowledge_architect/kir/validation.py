from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Protocol, TypeVar, runtime_checkable

from .extension import ExtensionDefinition, ExtensionRegistry
from .identity import EntityId, EvidenceId, KIRIdentity, KnowledgeUnitId, ProvenanceId
from .knowledge_unit import KnowledgeUnit
from .relation import Relation, RelationTargetKind
from .transformation import (
    KnowledgeUnitTransformation,
    RelationTransformationOutcome,
    TransformationKind,
    TransformationResult,
)


class ValidationSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ValidationMode(StrEnum):
    STRICT = "strict"
    PERMISSIVE = "permissive"


class ValidationCode(StrEnum):
    DUPLICATE_ID = "duplicate_id"
    INVALID_EXTENSION = "invalid_extension"
    INVALID_IDENTIFIER = "invalid_identifier"
    INVALID_MAPPING = "invalid_mapping"
    INVALID_RELATION = "invalid_relation"
    INVALID_TRANSFORMATION = "invalid_transformation"
    MISSING_PROVENANCE = "missing_provenance"
    MISSING_REFERENCE = "missing_reference"
    RELATION_REQUIRES_REVIEW = "relation_requires_review"


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    code: ValidationCode
    severity: ValidationSeverity
    message: str
    location: str = ""

    def __post_init__(self) -> None:
        message = self.message.strip()
        location = self.location.strip()
        if not message:
            raise ValueError("message must not be empty")
        object.__setattr__(self, "message", message)
        object.__setattr__(self, "location", location)

    @property
    def sort_key(self) -> tuple[int, str, str, str]:
        severity_order = {
            ValidationSeverity.ERROR: 0,
            ValidationSeverity.WARNING: 1,
            ValidationSeverity.INFO: 2,
        }
        return (
            severity_order[self.severity],
            self.code.value,
            self.location,
            self.message,
        )


class ValidationError(ValueError):
    def __init__(self, result: ValidationResult) -> None:
        self.result = result
        super().__init__(f"validation failed with {len(result.errors)} error(s)")


@dataclass(frozen=True, slots=True)
class ValidationResult:
    issues: tuple[ValidationIssue, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        sorted_issues = tuple(sorted(self.issues, key=lambda item: item.sort_key))
        object.__setattr__(self, "issues", sorted_issues)

    @property
    def valid(self) -> bool:
        return not self.errors

    @property
    def is_valid(self) -> bool:
        return self.valid

    @property
    def errors(self) -> tuple[ValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity is ValidationSeverity.ERROR)

    @property
    def warnings(self) -> tuple[ValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity is ValidationSeverity.WARNING)

    @property
    def infos(self) -> tuple[ValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity is ValidationSeverity.INFO)

    def add_issue(self, issue: ValidationIssue) -> ValidationResult:
        return ValidationResult((*self.issues, issue))

    def extend(self, other: ValidationResult | Iterable[ValidationIssue]) -> ValidationResult:
        additions = other.issues if isinstance(other, ValidationResult) else tuple(other)
        return ValidationResult((*self.issues, *additions))

    def has_errors(self) -> bool:
        return bool(self.errors)

    def raise_if_invalid(self) -> None:
        if not self.valid:
            raise ValidationError(self)


@dataclass(frozen=True, slots=True)
class ValidationContext:
    mode: ValidationMode = ValidationMode.STRICT
    entities: Mapping[EntityId, Any] = field(default_factory=dict)
    knowledge_units: Mapping[KnowledgeUnitId, KnowledgeUnit] = field(default_factory=dict)
    evidence: Mapping[EvidenceId, Any] = field(default_factory=dict)
    provenance: Mapping[ProvenanceId, Any] = field(default_factory=dict)
    extension_registry: ExtensionRegistry | None = None

    def __post_init__(self) -> None:
        for attribute in ("entities", "knowledge_units", "evidence", "provenance"):
            object.__setattr__(self, attribute, MappingProxyType(dict(getattr(self, attribute))))

    def policy_severity(self) -> ValidationSeverity:
        if self.mode is ValidationMode.PERMISSIVE:
            return ValidationSeverity.WARNING
        return ValidationSeverity.ERROR


T = TypeVar("T")


@runtime_checkable
class Validator(Protocol[T]):
    def validate(self, obj: T, context: ValidationContext) -> ValidationResult: ...


class ValidationRegistry:
    def __init__(self) -> None:
        self._validators: dict[type[Any], list[Validator[Any]]] = {}

    def register(self, object_type: type[T], validator: Validator[T]) -> None:
        validators = self._validators.setdefault(object_type, [])
        if validator in validators:
            raise ValueError("validator is already registered for object type")
        validators.append(validator)

    def validate(
        self,
        obj: Any,
        context: ValidationContext | None = None,
    ) -> ValidationResult:
        resolved_context = context or ValidationContext()
        result = ValidationResult()
        matched = False
        for object_type, validators in self._validators.items():
            if isinstance(obj, object_type):
                matched = True
                for validator in validators:
                    result = result.extend(validator.validate(obj, resolved_context))
        if not matched:
            raise KeyError(f"no validators registered for {type(obj).__name__}")
        return result

    def validators_for(self, object_type: type[Any]) -> tuple[Validator[Any], ...]:
        return tuple(self._validators.get(object_type, ()))


class IdentityValidator:
    def validate(self, obj: KIRIdentity, context: ValidationContext) -> ValidationResult:
        del context
        expected_prefix = f"{obj.prefix}:"
        if obj.value.startswith(expected_prefix):
            return ValidationResult()
        return ValidationResult(
            (
                ValidationIssue(
                    ValidationCode.INVALID_IDENTIFIER,
                    ValidationSeverity.ERROR,
                    f"identity must start with {expected_prefix!r}",
                    str(obj),
                ),
            )
        )


class KnowledgeUnitValidator:
    def validate(self, unit: KnowledgeUnit, context: ValidationContext) -> ValidationResult:
        issues: list[ValidationIssue] = []
        location = str(unit.id)

        if unit.provenance_id is None:
            issues.append(
                ValidationIssue(
                    ValidationCode.MISSING_PROVENANCE,
                    context.policy_severity(),
                    "knowledge unit has no provenance",
                    location,
                )
            )
        elif unit.provenance_id not in context.provenance:
            issues.append(
                ValidationIssue(
                    ValidationCode.MISSING_REFERENCE,
                    ValidationSeverity.ERROR,
                    f"unknown provenance reference: {unit.provenance_id}",
                    location,
                )
            )

        for entity_id in unit.subject_ids:
            if entity_id not in context.entities:
                issues.append(
                    ValidationIssue(
                        ValidationCode.MISSING_REFERENCE,
                        ValidationSeverity.ERROR,
                        f"unknown subject reference: {entity_id}",
                        location,
                    )
                )
        for evidence_id in unit.evidence_ids:
            if evidence_id not in context.evidence:
                issues.append(
                    ValidationIssue(
                        ValidationCode.MISSING_REFERENCE,
                        ValidationSeverity.ERROR,
                        f"unknown evidence reference: {evidence_id}",
                        location,
                    )
                )
        return ValidationResult(tuple(issues))


class RelationValidator:
    def validate(self, relation: Relation, context: ValidationContext) -> ValidationResult:
        issues: list[ValidationIssue] = []
        location = str(relation.id)
        for label, endpoint in (("source", relation.source), ("target", relation.target)):
            registry: Mapping[Any, Any]
            if endpoint.kind is RelationTargetKind.ENTITY:
                registry = context.entities
            else:
                registry = context.knowledge_units
            if endpoint.id not in registry:
                issues.append(
                    ValidationIssue(
                        ValidationCode.MISSING_REFERENCE,
                        ValidationSeverity.ERROR,
                        f"unknown {label} reference: {endpoint.id}",
                        location,
                    )
                )
        return ValidationResult(tuple(issues))


class TransformationValidator:
    def validate(
        self,
        transformation: KnowledgeUnitTransformation,
        context: ValidationContext,
    ) -> ValidationResult:
        issues: list[ValidationIssue] = []
        location = str(transformation.id)

        for source_id in transformation.source_ids:
            if source_id not in context.knowledge_units:
                issues.append(
                    ValidationIssue(
                        ValidationCode.MISSING_REFERENCE,
                        ValidationSeverity.ERROR,
                        f"unknown transformation source: {source_id}",
                        location,
                    )
                )
        if transformation.provenance_id not in context.provenance:
            issues.append(
                ValidationIssue(
                    ValidationCode.MISSING_REFERENCE,
                    ValidationSeverity.ERROR,
                    f"unknown transformation provenance: {transformation.provenance_id}",
                    location,
                )
            )

        source_count = len(transformation.source_ids)
        target_count = len(transformation.target_ids)
        if transformation.kind is TransformationKind.MERGE and not (
            source_count > 1 and target_count == 1
        ):
            issues.append(
                ValidationIssue(
                    ValidationCode.INVALID_TRANSFORMATION,
                    ValidationSeverity.ERROR,
                    "merge requires multiple sources and exactly one target",
                    location,
                )
            )
        if transformation.kind is TransformationKind.SPLIT and not (
            source_count == 1 and target_count > 1
        ):
            issues.append(
                ValidationIssue(
                    ValidationCode.INVALID_TRANSFORMATION,
                    ValidationSeverity.ERROR,
                    "split requires exactly one source and multiple targets",
                    location,
                )
            )

        for decision in transformation.relation_policy.decisions:
            if decision.outcome is RelationTransformationOutcome.REQUIRES_REVIEW:
                issues.append(
                    ValidationIssue(
                        ValidationCode.RELATION_REQUIRES_REVIEW,
                        context.policy_severity(),
                        f"relation decision requires review: {decision.source_relation_id}",
                        location,
                    )
                )
        return ValidationResult(tuple(issues))


class TransformationResultValidator:
    def validate(
        self,
        result: TransformationResult,
        context: ValidationContext,
    ) -> ValidationResult:
        issues = TransformationValidator().validate(result.transformation, context)
        location = str(result.transformation.id)
        if result.provenance.id not in context.provenance:
            issues = issues.add_issue(
                ValidationIssue(
                    ValidationCode.MISSING_REFERENCE,
                    ValidationSeverity.ERROR,
                    "result provenance is not present in validation context: "
                    f"{result.provenance.id}",
                    location,
                )
            )
        return issues


class ExtensionDefinitionValidator:
    def validate(
        self,
        definition: ExtensionDefinition,
        context: ValidationContext,
    ) -> ValidationResult:
        registry = context.extension_registry
        if registry is None:
            return ValidationResult()

        issues: list[ValidationIssue] = []
        location = str(definition.id)
        for dependency in definition.dependencies:
            registered = registry.by_id.get(dependency.extension_id)
            if registered is None:
                issues.append(
                    ValidationIssue(
                        ValidationCode.INVALID_EXTENSION,
                        ValidationSeverity.ERROR,
                        f"missing extension dependency: {dependency.extension_id}",
                        location,
                    )
                )
            elif registered.version != dependency.version:
                issues.append(
                    ValidationIssue(
                        ValidationCode.INVALID_EXTENSION,
                        ValidationSeverity.ERROR,
                        "extension dependency version mismatch: "
                        f"expected {dependency.version}, found {registered.version}",
                        location,
                    )
                )
        return ValidationResult(tuple(issues))


def core_validation_registry() -> ValidationRegistry:
    registry = ValidationRegistry()
    registry.register(KIRIdentity, IdentityValidator())
    registry.register(KnowledgeUnit, KnowledgeUnitValidator())
    registry.register(Relation, RelationValidator())
    registry.register(KnowledgeUnitTransformation, TransformationValidator())
    registry.register(TransformationResult, TransformationResultValidator())
    registry.register(ExtensionDefinition, ExtensionDefinitionValidator())
    return registry
