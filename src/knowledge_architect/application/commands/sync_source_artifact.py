from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SyncSourceArtifactCommand:
    """Request synchronization of one artifact from a registered source."""

    source_id: str
