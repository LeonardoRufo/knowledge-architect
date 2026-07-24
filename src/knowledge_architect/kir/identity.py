from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class KIRIdentity:
    """Typed immutable identity used by every KIR core object."""

    value: str

    prefix: ClassVar[str] = "kir"

    def __post_init__(self) -> None:
        expected = f"{self.prefix}:"
        if not self.value.startswith(expected):
            raise ValueError(f"Identity must start with {expected!r}")
        raw = self.value.removeprefix(expected)
        try:
            UUID(raw)
        except ValueError as exc:
            raise ValueError("Identity suffix must be a UUID") from exc

    @classmethod
    def new(cls) -> KIRIdentity:
        return cls(f"{cls.prefix}:{uuid4()}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class EntityId(KIRIdentity):
    prefix: ClassVar[str] = "entity"


@dataclass(frozen=True, slots=True)
class KnowledgeUnitId(KIRIdentity):
    prefix: ClassVar[str] = "knowledge-unit"


@dataclass(frozen=True, slots=True)
class RelationId(KIRIdentity):
    prefix: ClassVar[str] = "relation"


@dataclass(frozen=True, slots=True)
class EvidenceId(KIRIdentity):
    prefix: ClassVar[str] = "evidence"


@dataclass(frozen=True, slots=True)
class ProvenanceId(KIRIdentity):
    prefix: ClassVar[str] = "provenance"
