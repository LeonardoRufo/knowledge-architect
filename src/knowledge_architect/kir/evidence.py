from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .identity import EvidenceId


class EvidenceKind(StrEnum):
    SOURCE_EXCERPT = "source_excerpt"
    OBSERVATION = "observation"
    MEASUREMENT = "measurement"
    TESTIMONY = "testimony"


@dataclass(frozen=True, slots=True)
class Evidence:
    """Immutable support for one or more knowledge units."""

    id: EvidenceId
    kind: EvidenceKind
    source_system: str
    source_id: str
    content: str
    locator: str | None = None

    def __post_init__(self) -> None:
        for name in ("source_system", "source_id", "content"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} must not be empty")
        if self.locator is not None and not self.locator.strip():
            raise ValueError("locator must be None or non-empty")
