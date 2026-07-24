from __future__ import annotations

from dataclasses import dataclass, field

from .identity import EntityId


def _validate_non_empty(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} must not be empty")


@dataclass(frozen=True, slots=True)
class Entity:
    """A stable referent mentioned or described by knowledge units."""

    id: EntityId
    kind: str
    label: str
    aliases: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        _validate_non_empty(self.kind, "kind")
        _validate_non_empty(self.label, "label")
        normalized_aliases = tuple(alias.strip() for alias in self.aliases)
        if any(not alias for alias in normalized_aliases):
            raise ValueError("aliases must not contain empty values")
        if len(set(normalized_aliases)) != len(normalized_aliases):
            raise ValueError("aliases must be unique")
        object.__setattr__(self, "aliases", normalized_aliases)
