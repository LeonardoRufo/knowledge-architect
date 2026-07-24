from __future__ import annotations

from collections.abc import Iterable

from knowledge_architect.ports import ProjectionPort


class ProjectionRegistry:
    def __init__(self, projections: Iterable[ProjectionPort]) -> None:
        self._projections = {projection.name: projection for projection in projections}

    def get(self, name: str) -> ProjectionPort:
        try:
            return self._projections[name]
        except KeyError as exc:
            available = ", ".join(sorted(self._projections)) or "none"
            raise ValueError(f"Unknown projection {name!r}; available: {available}") from exc

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._projections))
