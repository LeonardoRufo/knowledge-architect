from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SyncSourceArtifactResult:
    """Observable result returned by the synchronization use case."""

    inserted: int
    source_system: str
    source_id: str
    title: str
