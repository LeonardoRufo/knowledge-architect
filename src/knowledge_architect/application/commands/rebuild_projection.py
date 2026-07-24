from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RebuildProjectionCommand:
    projection_name: str
