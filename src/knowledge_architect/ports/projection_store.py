from __future__ import annotations

from typing import Any, Protocol


class ProjectionStorePort(Protocol):
    """Persistence contract for versioned projection snapshots."""

    def replace(
        self,
        *,
        name: str,
        version: int,
        last_sequence: int,
        state: dict[str, Any],
    ) -> None: ...

    def load(self, name: str) -> dict[str, Any] | None: ...
